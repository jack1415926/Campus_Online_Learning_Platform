// LMS Main Application - Vue 3 SPA (Complete)
const { createApp, ref, reactive, computed, onMounted, onUnmounted, watch, nextTick, shallowRef } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;
function navigate(path) { window.location.hash = "#" + path; }

// Global reactive unread-count state shared between the app header/menu badges
// and the notification page, so that marking-all-read updates every badge.
const unreadState = reactive({ count: 0 });
const loadUnread = async () => { try { const r = await api.getUnreadCount(); unreadState.count = r.count || 0; } catch(e) {} };

// ===== Responsive detection (shared across all components) =====
const windowWidth = ref(window.innerWidth);
const isMobile = computed(() => windowWidth.value <= 768);
const isTablet = computed(() => windowWidth.value > 768 && windowWidth.value <= 1024);
window.addEventListener('resize', () => { windowWidth.value = window.innerWidth; });

const STATUS_MAP = { draft: { t: "草稿", c: "info" }, pending_review: { t: "审核中", c: "warning" }, published: { t: "已发布", c: "success" }, archived: { t: "已下架", c: "danger" } };
const DIFF_MAP = { beginner: { t: "入门", c: "success" }, intermediate: { t: "中级", c: "warning" }, advanced: { t: "高级", c: "danger" } };
const TYPE_MAP = { video: "视频", document: "文档", text: "文字", image: "图片", scorm: "SCORM" };

// ===== Login =====
const LoginPage = {
  template: `<div class="login-container"><div class="login-card">
    <div class="login-title">校园在线学习平台</div><p style="text-align:center;color:#909399">课程 · 学习 · 交流</p>
    <el-form v-if="mode==='login'" label-position="top" @submit.prevent="doLogin">
      <el-form-item label="用户名 / 邮箱"><el-input v-model="lf.username" placeholder="请输入用户名或邮箱" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="lf.password" type="password" placeholder="请输入密码" show-password /></el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">登录</el-button>
      <el-button text @click="mode='register'" style="margin-top:12px">注册新账号</el-button>
    </el-form>
    <el-form v-else label-position="top" @submit.prevent="doRegister">
      <el-form-item label="用户名"><el-input v-model="rf.username" placeholder="至少3个字符" /></el-form-item>
      <el-form-item label="姓名"><el-input v-model="rf.full_name" placeholder="请输入姓名" /></el-form-item>
      <el-form-item label="邮箱"><el-input v-model="rf.email" placeholder="请输入邮箱" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="rf.password" type="password" placeholder="至少8个字符" show-password /></el-form-item>
      <el-form-item label="注册身份"><el-radio-group v-model="rf.role"><el-radio value="student">学生</el-radio><el-radio value="teacher">教师（需审核）</el-radio></el-radio-group></el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading">提交注册</el-button><el-button @click="mode='login'">返回登录</el-button>
    </el-form>
  </div></div>`,
  setup() {
    const mode=ref('login'), loading=ref(false);
    const lf=reactive({username:'',password:''}), rf=reactive({username:'',full_name:'',email:'',password:'',role:'student'});
    const doLogin=async()=>{if(!lf.username||!lf.password)return ElMessage.warning('请填写用户名和密码');loading.value=true;try{const r=await api.login(lf);api.setToken(r.access_token);window.location.hash='#dashboard';window.location.reload();}catch(e){ElMessage.error(e.message);}finally{loading.value=false;}};
    const doRegister=async()=>{loading.value=true;try{const r=await api.register({...rf});ElMessage.success(r.message);lf.username=rf.username;lf.password='';rf.password='';mode.value='login';}catch(e){ElMessage.error(e.message);}finally{loading.value=false;}};
    return {mode,loading,lf,rf,doLogin,doRegister};
  }
};

// ===== Dashboard =====
const DashboardPage = {
  template: `<div><h2 style="margin-bottom:16px">欢迎来到校园在线学习平台</h2>
    <el-alert v-if="!api.hasPerm('course:read')" title="教师账号尚未通过审核，请到个人中心查看审核状态和原因" type="info" :closable="false" />
    <el-card v-else><template #header>最近课程</template><el-table :data="courses">
      <el-table-column prop="title" label="课程名称" /><el-table-column prop="instructor" label="任课教师" />
      <el-table-column label="状态"><template #default="{row}"><el-tag :type="STATUS_MAP[row.status]?.c">{{STATUS_MAP[row.status]?.t}}</el-tag></template></el-table-column>
      <el-table-column label="操作"><template #default="{row}"><el-button text type="primary" @click="navigate('course/'+row.id)">查看课程</el-button></template></el-table-column>
    </el-table></el-card>
  </div>`,
  setup(){const courses=ref([]);onMounted(async()=>{if(!api.hasPerm('course:read'))return;try{const r=await api.listCourses({page:1,page_size:5,managed:api.hasRole('teacher')});courses.value=r.items;}catch(e){ElMessage.error(e.message);}});return{courses,api,STATUS_MAP,navigate};}
};

// ===== Course List =====
const CourseListPage = {
  template: `
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>课程中心</h2>
      <div>
        <el-input v-model="keyword" placeholder="搜索课程" style="width:200px;margin-right:8px" clearable @keyup.enter="load" />
        <el-switch v-if="api.hasRole('teacher')" v-model="managed" active-text="我的教学课程" inactive-text="已发布课程" @change="load" style="margin-right:12px" /><el-select v-if="api.hasPerm('course:create')" v-model="statusFilter" placeholder="状态" style="width:120px;margin-right:8px" clearable @change="load">
          <el-option label="已发布" value="published" /><el-option label="草稿" value="draft" /><el-option label="审核中" value="pending_review" /><el-option label="已下架" value="archived" />
        </el-select>
        <el-button type="primary" v-if="api.hasPerm('course:create')" @click="showCreate=true">创建课程</el-button>
      </div>
    </div>
    <el-row :gutter="16">
      <el-col :span="6" v-for="c in courses" :key="c.id" style="margin-bottom:16px">
        <el-card class="course-card" shadow="hover" @click="navigate('course/'+c.id)">
          <div class="course-cover" :style="{background: coverColor(c.title)}"><img v-if="c.cover_preview_url" :src="c.cover_preview_url" style="width:100%;height:100%;object-fit:cover"/><span v-else>{{ (c.title||'?')[0] }}</span></div>
          <div style="padding:12px 0"><el-tag size="small" :type="STATUS_MAP[c.status]?.c">{{STATUS_MAP[c.status]?.t}}</el-tag><span style="margin-left:8px">{{c.instructor}}</span>
            <div style="font-weight:bold;font-size:15px;margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ c.title }}</div>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <el-tag size="small" :type="DIFF_MAP[c.difficulty]?.c">{{ DIFF_MAP[c.difficulty]?.t }}</el-tag>
              <span style="font-size:12px;color:#909399">{{ c.estimated_minutes }}分钟</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-pagination v-if="total>0" :total="total" :page-size="pageSize" v-model:current-page="page" layout="prev, pager, next" style="margin-top:16px" @current-change="load" />
    <el-dialog v-model="showCreate" title="创建课程" width="500px">
      <el-form :model="form" label-position="top">
        <el-form-item label="课程标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="课程描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="难度"><el-select v-model="form.difficulty" style="width:100%"><el-option label="入门" value="beginner" /><el-option label="中级" value="intermediate" /><el-option label="高级" value="advanced" /></el-select></el-form-item>
        <el-form-item label="预计学时(分钟)"><el-input-number v-model="form.estimated_minutes" :min="0" /></el-form-item>
        <el-form-item label="封面"><input type="file" accept="image/jpeg,image/png" @change="uploadCover"/><span v-if="form.cover_image_url">封面已上传</span></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" :loading="creating" @click="doCreate">创建</el-button></template>
    </el-dialog>
  </div>`,
  setup() {
    const courses = ref([]); const total = ref(0); const page = ref(1); const pageSize = 12;
    const keyword = ref(""); const statusFilter = ref(""); const managed=ref(api.hasRole("teacher"));
    const showCreate = ref(false); const creating = ref(false);
    const form = reactive({ title:"", description:"", difficulty:"beginner", estimated_minutes:60, instructor:"", cover_image_url:"", tag_ids:[] });
    const coverColor = (t) => { const colors = ["linear-gradient(135deg,#7c3aed,#4c1d95)","linear-gradient(135deg,#f093fb,#f5576c)","linear-gradient(135deg,#8b5cf6,#d946ef)","linear-gradient(135deg,#43e97b,#38f9d7)"]; return colors[(t||"").charCodeAt(0) % colors.length]; };
    const load = async () => {
      try { const params = { page: page.value, page_size: pageSize, managed:managed.value }; if (keyword.value) params.keyword = keyword.value; if (statusFilter.value) params.status = statusFilter.value; const r = await api.listCourses(params); courses.value = r.items || []; total.value = r.meta.total; } catch(e) { ElMessage.error(e.message); }
    };
    const doCreate = async () => {
      if (!form.title) return ElMessage.warning("请输入标题");
      creating.value = true;
      try { await api.createCourse({ ...form, chapters: [] }); ElMessage.success("创建成功"); showCreate.value = false; load(); form.title=""; form.description=""; } catch(e) { ElMessage.error(e.message); }
      creating.value = false;
    };
    const uploadCover=async(event)=>{const file=event.target.files[0];if(!file)return;try{const asset=await api.uploadMedia(file);form.cover_image_url=asset.file_url;ElMessage.success("封面已上传");}catch(e){ElMessage.error(e.message);}};
    onMounted(load);
    return { courses, total, page, pageSize, keyword, statusFilter, showCreate, creating, form, load, doCreate, DIFF_MAP, STATUS_MAP, managed, uploadCover, navigate, coverColor };
  }
};

// ===== Course Detail with REAL learning =====
const CourseDetailPage = {
  components: { HomeworkPanel, CampusExamPanel },
  props: ["id"],
  template: `
  <div v-if="course">
    <el-page-header @back="navigate('courses')" style="margin-bottom:16px"><template #content><span style="font-size:18px;font-weight:bold">{{ course.title }}</span></template></el-page-header>
    <el-alert v-if="course.review_reason" :title="'审核驳回：'+course.review_reason" type="warning" :closable="false" style="margin-bottom:12px"/><el-button v-if="api.hasRole('student')&&!course.is_enrolled&&course.status==='published'" type="primary" @click="joinCourse" style="margin-bottom:12px">加入学习</el-button><el-alert v-if="!canManage&&!course.can_learn" title="加入学习后可查看完整章节内容" type="info" :closable="false" style="margin-bottom:12px"/><el-row :gutter="20">
      <el-col :span="course.can_learn?16:24">
        <el-card shadow="never" style="margin-bottom:16px">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="难度"><el-tag :type="DIFF_MAP[course.difficulty]?.c">{{ DIFF_MAP[course.difficulty]?.t }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="预计学时">{{ course.estimated_minutes }} 分钟</el-descriptions-item>
            <el-descriptions-item label="讲师">{{ course.instructor || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态"><el-tag :type="STATUS_MAP[course.status]?.c">{{ STATUS_MAP[course.status]?.t }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ course.description || '暂无描述' }}</el-descriptions-item>
          </el-descriptions>
          <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap" v-if="canManage">
            <el-button size="small" type="primary" v-if="course.can_edit" @click="openEdit">编辑课程</el-button>
            <el-button size="small" type="danger" plain v-if="course.can_edit" @click="doDelete">删除课程</el-button>
            <el-button size="small" type="warning" v-if="course.can_edit" @click="publish('submit_review')">提交审核</el-button>
            <el-button size="small" type="success" v-if="course.status==='pending_review' && api.hasPerm('course:publish')" @click="publish('publish')">通过并发布</el-button><el-button size="small" type="warning" v-if="course.status==='pending_review'&&api.hasRole('admin')" @click="publish('reject')">驳回课程</el-button>
            <el-button size="small" v-if="course.status==='published' && api.hasPerm('course:publish')" @click="publish('archive')">归档</el-button><el-button size="small" v-if="['published','archived'].includes(course.status)&&api.hasRole('admin')" @click="publish('unpublish')">退回草稿</el-button>
          </div>
        </el-card>

        <el-card shadow="never" style="margin-bottom:16px" v-if="activeChapter && (canManage || course.can_learn)">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>{{ activeChapter.title }} <el-tag size="small">{{ TYPE_MAP[activeChapter.content_type] }}</el-tag></span>
              <el-button size="small" v-if="course.can_edit" @click="openEditCh(activeChapter)">编辑章节</el-button>
            </div>
          </template>
          <div v-if="activeChapter.content_type==='video'" class="course-video">
            <video v-if="videoUrl" :key="activeChapter.id" :src="videoUrl" controls style="width:100%;max-height:400px" @timeupdate="onVideoTime" @pause="saveVideo" @ended="onVideoEnded" @loadedmetadata="onVideoLoaded"></video>
            <div v-else style="padding:40px;text-align:center;color:#909399">
              <el-icon size="48"><VideoPlay /></el-icon>
              <p v-if="activeChapter.content_ref_id">正在加载视频...</p>
              <p v-else>本章节未关联视频素材，请点击“编辑章节”关联</p>
            </div>
          </div>
          <div v-else-if="activeChapter.content_type==='document'">
            <div v-if="docUrl" style="width:100%">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;padding:0 4px;flex-wrap:wrap;gap:8px">
                <span style="font-size:13px;color:#909399;flex:1;min-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ docFileName }}</span>
                <div style="display:flex;align-items:center;gap:4px;flex-shrink:0">
                  <template v-if="isPdfDoc && pdfTotalPages>0">
                    <el-button size="small" text @click="pdfPrev" :disabled="pdfPageNum<=1"><el-icon><ArrowLeft /></el-icon></el-button>
                    <span style="font-size:12px;color:#606266;white-space:nowrap">{{ pdfPageNum }}/{{ pdfTotalPages }}</span>
                    <el-button size="small" text @click="pdfNext" :disabled="pdfPageNum>=pdfTotalPages"><el-icon><ArrowRight /></el-icon></el-button>
                    <el-button size="small" text @click="pdfZoomOut"><el-icon><ZoomOut /></el-icon></el-button>
                    <el-button size="small" text @click="pdfZoomIn"><el-icon><ZoomIn /></el-icon></el-button>
                  </template>
                  <el-button size="small" type="primary" text @click="downloadDoc"><el-icon><Download /></el-icon> 下载</el-button>
                </div>
              </div>
              <div v-if="isPdfDoc" style="width:100%;border:1px solid #ebeef5;border-radius:8px;background:#fafafa;overflow:auto">
                <div v-if="pdfLoading" style="padding:60px;text-align:center;color:#909399"><el-icon size="32" class="is-loading"><Loading /></el-icon><p style="margin-top:8px">正在加载PDF...</p></div>
                <canvas ref="pdfCanvas" style="display:block;margin:0 auto"></canvas>
              </div>
              <div v-else style="width:100%;height:400px;border:1px solid #ebeef5;border-radius:8px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#fafafa">
                <el-icon size="64" color="#7c3aed"><Document /></el-icon>
                <p style="margin-top:16px;color:#606266;font-size:15px">{{ docFileName }}</p>
                <p style="margin-top:4px;color:#909399;font-size:13px">浏览器无法在线预览此类型文件，请点击下载查看</p>
                <el-button type="primary" style="margin-top:16px" @click="downloadDoc"><el-icon><Download /></el-icon> 下载文件</el-button>
              </div>
            </div>
            <div v-else style="padding:40px;text-align:center;color:#909399">
              <el-icon size="48"><Document /></el-icon>
              <p v-if="activeChapter.content_ref_id">正在加载文档...</p>
              <p v-else>本章节未关联文档素材，请点击“编辑章节”关联</p>
            </div>
          </div>
          <div v-else-if="activeChapter.content_type==='text'">
            <div style="padding:20px;line-height:1.8;font-size:15px;white-space:pre-wrap">{{activeChapter.text_content || '暂无内容'}}</div>
          </div>
          <div v-else-if="activeChapter.content_type==='image'">
            <div style="padding:20px;text-align:center">
              <img v-if="imageUrl" :src="imageUrl" style="max-width:100%;border-radius:8px" />
              <div v-else style="color:#909399">
                <el-icon size="48"><Picture /></el-icon>
                <p>暂无图片</p>
              </div>
            </div>
          </div>
          <div style="margin-top:16px;text-align:center">
            <el-button type="primary" v-if="course.can_learn&&course.status==='published'" @click="completeChapter(activeChapter)" :disabled="activeChapter.content_type==='video' && !videoCompleted">{{ activeChapter.content_type==='video' && !videoCompleted ? '视频未播完' : '标记完成' }}</el-button>
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>课程章节</span>
              <el-button size="small" type="primary" @click="openAddCh" v-if="course.can_edit">添加章节</el-button>
            </div>
          </template>
          <div v-for="(ch, i) in course.chapters" :key="ch.id" class="chapter-item" :class="{active: activeChapter?.id===ch.id}" @click="selectChapter(ch)">
            <div style="display:flex;align-items:center;gap:12px">
              <el-tag :type="ch.is_required?'danger':'info'" size="small">{{ ch.is_required ? '必修' : '选修' }}</el-tag>
              <span style="font-weight:500">{{ i+1 }}. {{ ch.title }}</span>
              <el-tag size="small" effect="plain">{{ TYPE_MAP[ch.content_type] }}</el-tag>
              <el-icon v-if="completedChapters.has(ch.id)" color="#67c23a"><CircleCheck /></el-icon>
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span style="font-size:12px;color:#909399;margin-right:4px">{{ ch.estimated_minutes }}分钟</span>
              <el-button size="small" type="primary" @click.stop="selectChapter(ch)" v-if="canManage || course.can_learn">{{ canManage ? '预览' : '学习' }}</el-button>
              <el-button size="small" text @click.stop="openEditCh(ch)" v-if="course.can_edit">编辑</el-button>
              <el-button size="small" type="danger" text @click.stop="delChapter(ch)" v-if="course.can_edit">删除</el-button>
            </div>
          </div>
          <el-empty v-if="!course.chapters||course.chapters.length===0" description="暂无章节" />
        </el-card>
      </el-col>
      <el-col :span="8" v-if="course.can_learn">
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header><span>学习进度</span></template>
          <el-progress :percentage="progress.overall_percent||0" :status="progress.is_complete?'success':''" />
          <el-descriptions :column="1" size="small" style="margin-top:16px">
            <el-descriptions-item label="总章节">{{ progress.total_chapters }}</el-descriptions-item>
            <el-descriptions-item label="已完成">{{ progress.completed_chapters }}</el-descriptions-item>
            <el-descriptions-item label="学习时长">{{ Math.round((progress.total_learning_seconds||0)/60) }}分钟</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="progress.is_complete?'success':(statusText==='待考试'?'warning':(statusText==='学习中'?'warning':'info'))" size="small">{{ statusText }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <div v-if="progress.exam_required && progress.exams && progress.exams.length" style="margin-top:16px">
            <div style="font-weight:bold;font-size:13px;margin-bottom:8px">课程考试</div>
            <div v-for="ex in progress.exams" :key="ex.exam_id" style="display:flex;justify-content:space-between;align-items:center;padding:8px;border:1px solid #ebeef5;border-radius:6px;margin-bottom:8px">
              <div style="flex:1">
                <div style="font-size:13px">{{ ex.title }}</div>
                <div style="font-size:12px;color:#909399;margin-top:2px">
                  <el-tag v-if="ex.passed" type="success" size="small">已通过</el-tag>
                  <el-tag v-else type="warning" size="small">未通过</el-tag>
                  <span style="margin-left:6px">已考 {{ ex.attempts }}/{{ ex.max_attempts }} 次</span>
                </div>
              </div>
              <el-button size="small" type="primary" @click="goExam(ex.exam_id)" :disabled="!progress.can_take_exam || ex.passed">{{ !progress.can_take_exam ? '学完章节可考' : (ex.passed ? '已通过' : '去考试') }}</el-button>
            </div>
          </div>
          <div v-if="progress.is_complete" style="margin-top:16px;text-align:center">
            
          </div>
          <div v-else-if="progress.can_take_exam && progress.exam_required" style="margin-top:16px;text-align:center">
            <span style="font-size:12px;color:#e6a23c">章节已学完，请完成考试后课程才算完成</span>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <homework-panel :course="course" :key="course.id"/>
    <campus-exam-panel :course="course" :key="course.id"/>

    <el-dialog v-model="showEdit" title="编辑课程" width="500px">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="标题"><el-input v-model="editForm.title" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="editForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="难度"><el-select v-model="editForm.difficulty" style="width:100%"><el-option label="入门" value="beginner" /><el-option label="中级" value="intermediate" /><el-option label="高级" value="advanced" /></el-select></el-form-item>
        <el-form-item label="学时(分钟)"><el-input-number v-model="editForm.estimated_minutes" :min="0" /></el-form-item>
        <el-form-item label="任课教师"><el-input v-model="editForm.instructor" disabled /></el-form-item>
        <el-form-item label="封面"><input type="file" accept="image/jpeg,image/png" @change="uploadEditCover"/><span v-if="editForm.cover_image_url">已设置封面</span></el-form-item>
      </el-form>
      <template #footer><el-button @click="showEdit=false">取消</el-button><el-button type="primary" @click="doEdit">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="showAddCh" title="添加章节" width="600px">
      <el-form :model="chForm" label-position="top">
        <el-form-item label="章节标题"><el-input v-model="chForm.title" /></el-form-item>
        <el-form-item label="内容类型"><el-select v-model="chForm.content_type" style="width:100%" @change="onTypeChange"><el-option label="视频" value="video" /><el-option label="文档" value="document" /><el-option label="图片" value="image" /><el-option label="文字" value="text" /></el-select></el-form-item>
        <el-form-item label="文字内容" v-if="chForm.content_type==='text'"><el-input v-model="chForm.text_content" type="textarea" :rows="4" placeholder="输入文字内容" /></el-form-item>
        <el-form-item label="关联素材" v-if="chForm.content_type==='video'||chForm.content_type==='document'||chForm.content_type==='image'">
          <div style="display:flex;gap:8px;width:100%">
            <el-select v-model="chForm.content_ref_id" filterable clearable placeholder="选择素材库中的文件" style="flex:1">
              <el-option v-for="m in mediaList" :key="m.id" :label="m.name" :value="m.id">
                <span>{{ m.name }}</span><el-tag size="small" style="margin-left:8px">{{ m.media_type }}</el-tag>
              </el-option>
            </el-select>
            <el-button @click="loadMedia">刷新</el-button>
          </div>
          <div v-if="chForm.content_ref_id" style="margin-top:8px;color:#67c23a;font-size:13px">已选择: {{ selectedMediaName }}</div>
        </el-form-item>
        <el-form-item label="学时(分钟)"><el-input-number v-model="chForm.estimated_minutes" :min="0" /></el-form-item>
        <el-form-item label="必修"><el-switch v-model="chForm.is_required" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showAddCh=false">取消</el-button><el-button type="primary" @click="doAddCh">添加</el-button></template>
    </el-dialog>

    <el-dialog v-model="showEditCh" title="编辑章节" width="600px">
      <el-form :model="editChForm" label-position="top">
        <el-form-item label="章节标题"><el-input v-model="editChForm.title" /></el-form-item>
        <el-form-item label="内容类型"><el-select v-model="editChForm.content_type" style="width:100%" @change="onEditTypeChange"><el-option label="视频" value="video" /><el-option label="文档" value="document" /><el-option label="图片" value="image" /><el-option label="文字" value="text" /></el-select></el-form-item>
        <el-form-item label="文字内容" v-if="editChForm.content_type==='text'"><el-input v-model="editChForm.text_content" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="关联素材" v-if="editChForm.content_type==='video'||editChForm.content_type==='document'||editChForm.content_type==='image'">
          <div style="display:flex;gap:8px;width:100%">
            <el-select v-model="editChForm.content_ref_id" filterable clearable placeholder="选择素材库中的文件" style="flex:1">
              <el-option v-for="m in mediaList" :key="m.id" :label="m.name" :value="m.id"><span>{{ m.name }}</span><el-tag size="small" style="margin-left:8px">{{ m.media_type }}</el-tag></el-option>
            </el-select>
            <el-button @click="loadMedia">刷新</el-button>
          </div>
        </el-form-item>
        <el-form-item label="学时(分钟)"><el-input-number v-model="editChForm.estimated_minutes" :min="0" /></el-form-item>
        <el-form-item label="必修"><el-switch v-model="editChForm.is_required" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showEditCh=false">取消</el-button><el-button type="primary" @click="doEditCh">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="showExamConfig" title="关联考试" width="600px">
      <div style="font-size:13px;color:#909399;margin-bottom:12px">所有章节学完后需通过以下全部考试，课程才算完成。可为每门考试单独设置重考次数。</div>
      <div v-for="(link, idx) in examLinks" :key="idx" style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <el-select v-model="link.exam_id" filterable placeholder="选择考试" style="flex:1">
          <el-option v-for="ex in allExams" :key="ex.id" :label="ex.title" :value="ex.id" />
        </el-select>
        <span style="font-size:13px;white-space:nowrap">重考</span>
        <el-input-number v-model="link.max_attempts" :min="1" :max="100" style="width:100px" />
        <span style="font-size:13px;white-space:nowrap">次</span>
        <el-button text type="danger" @click="removeExamLink(idx)"><el-icon><Delete /></el-icon></el-button>
      </div>
      <div style="margin-top:8px"><el-button size="small" @click="addExamLink">添加考试</el-button></div>
      <template #footer>
        <el-button @click="showExamConfig=false">取消</el-button>
        <el-button type="primary" @click="saveExamConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>`,
  setup(props) {
    const course = ref(null); const progress = ref({}); const activeChapter = ref(null);
    const showEdit = ref(false); const showAddCh = ref(false); const showEditCh = ref(false);
    const canManage = ref(false); const completedChapters = ref(new Set()); let courseStartTime = null;
    const chapterRecords = ref([]); let videoElement=null, lastVideoSave=0, videoSaving=false;
    const editForm = reactive({ title:"", description:"", difficulty:"beginner", estimated_minutes:0, instructor:"" });
    const chForm = reactive({ title:"", content_type:"video", text_content:"", content_ref_id:"", estimated_minutes:10, is_required:true, sort_order:0 });
    const editChForm = reactive({ title:"", content_type:"video", text_content:"", content_ref_id:"", estimated_minutes:0, is_required:true });
    const mediaList = ref([]);
    const selectedMediaName = computed(() => { const m = mediaList.value.find(x => x.id === chForm.content_ref_id); return m ? m.name : ""; });
    const videoUrl = ref(""); const docUrl = ref(""); const docFileName = ref(""); const imageUrl = ref(""); const pdfCanvas = ref(null); let learnSeconds = 0; let maxWatchedTime = 0; const videoCompleted = ref(false); const videoDuration = ref(0); const pdfDoc = shallowRef(null); const pdfPageNum = ref(1); const pdfTotalPages = ref(0); const pdfScale = ref(1.2); const pdfLoading = ref(false);
    const statusText = computed(() => {
      if (progress.value.is_complete) return "已完成";
      if (progress.value.can_take_exam && progress.value.exam_required) return "待考试";
      if (progress.value.status === "in_progress") return "学习中";
      return "未开始";
    });
    const goExam = (examId) => { navigate("exam/" + examId); };
    const isPdfDoc = computed(() => (docFileName.value || "").toLowerCase().endsWith(".pdf"));
    const downloadDoc = () => { if (docUrl.value) window.open(docUrl.value, "_blank"); };
    const renderPdfPage = async () => {
      if (!pdfDoc.value || !pdfCanvas.value) return;
      const page = await pdfDoc.value.getPage(pdfPageNum.value);
      const canvas = pdfCanvas.value;
      const ctx = canvas.getContext("2d");
      const dpr = window.devicePixelRatio || 1;
      const viewport = page.getViewport({ scale: pdfScale.value * dpr });
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      canvas.style.width = (viewport.width / dpr) + "px";
      canvas.style.height = (viewport.height / dpr) + "px";
      await page.render({ canvasContext: ctx, viewport }).promise;
    };
    const loadPdf = async (url) => {
      if (!url || !window.pdfjsLib) return;
      pdfLoading.value = true;
      try {
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = "https://unpkg.com/pdfjs-dist@2.16.105/build/pdf.worker.min.js";
        const task = window.pdfjsLib.getDocument(url);
        pdfDoc.value = await task.promise;
        pdfTotalPages.value = pdfDoc.value.numPages;
        pdfPageNum.value = 1;
        await nextTick();
        await renderPdfPage();
      } catch(e) { ElMessage.error("PDF加载失败: " + e.message); }
      pdfLoading.value = false;
    };
    const pdfPrev = async () => { if (pdfPageNum.value > 1) { pdfPageNum.value--; await renderPdfPage(); } };
    const pdfNext = async () => { if (pdfPageNum.value < pdfTotalPages.value) { pdfPageNum.value++; await renderPdfPage(); } };
    const pdfZoomIn = async () => { pdfScale.value = Math.min(pdfScale.value + 0.3, 3); await renderPdfPage(); };
    const pdfZoomOut = async () => { pdfScale.value = Math.max(pdfScale.value - 0.3, 0.5); await renderPdfPage(); };
    const fullscreenPdf = () => {};  // kept for compatibility
    let editingChapter = null;
    const showExamConfig = ref(false); const examLinks = ref([]); const allExams = ref([]);

    const loadExamOptions = async () => { try { const r = await api.listExams({ page:1, page_size:100 }); allExams.value = (r.items || []).map(e => ({ id: e.id, title: e.title })); } catch(e) {} };
    const openExamConfig = () => {
      const cc = course.value.completion_config || {};
      const links = (cc.exams || []).map(l => ({ exam_id: l.exam_id, max_attempts: l.max_attempts || 10 }));
      examLinks.value = links.length ? links : [{ exam_id: "", max_attempts: 10 }];
      loadExamOptions();
      showExamConfig.value = true;
    };
    const addExamLink = () => { examLinks.value.push({ exam_id: "", max_attempts: 10 }); };
    const removeExamLink = (idx) => { examLinks.value.splice(idx, 1); };
    const saveExamConfig = async () => {
      const valid = examLinks.value.filter(l => l.exam_id);
      if (!valid.length) return ElMessage.warning("请至少选择一门考试，或取消关联");
      const completion_config = { exam_mode: "all", exams: valid.map(l => ({ exam_id: l.exam_id, max_attempts: l.max_attempts || 10 })) };
      try { await api.updateCourse(props.id, { completion_config }); ElMessage.success("保存成功"); showExamConfig.value = false; load(); } catch(e) { ElMessage.error(e.message); }
    };
    const loadMedia = async (contentType) => {
      try {
        const type = contentType || "document";
        const r = await api.listMedia({ page:1, page_size:100, media_type: type });
        let items = r.items || [];
        if (type === "document") items = items.filter(m => /\.(pdf|docx)$/i.test(m.name || ""));
        mediaList.value = items;
      } catch(e) {}
    };
    const onTypeChange = () => { chForm.content_ref_id = ""; if (chForm.content_type === "video" || chForm.content_type === "document" || chForm.content_type === "image") loadMedia(chForm.content_type); };
    const onEditTypeChange = () => { editChForm.content_ref_id = ""; if (editChForm.content_type === "video" || editChForm.content_type === "document" || editChForm.content_type === "image") loadMedia(editChForm.content_type); };

    const load = async () => {
      try {
        await saveVideo();videoElement=null;
        course.value = await api.getCourse(props.id);
        if(course.value.can_learn){try { progress.value = await api.getCourseProgress(props.id); } catch(e) {}}
        canManage.value = course.value.can_manage;
        chapterRecords.value = course.value.can_learn ? await api.getMyRecords(props.id) : [];
        completedChapters.value = new Set(chapterRecords.value.filter(r => r.status === "completed").map(r => r.chapter_id));
        courseStartTime = Date.now();
        Object.assign(editForm, { title: course.value.title, description: course.value.description||"", difficulty: course.value.difficulty, estimated_minutes: course.value.estimated_minutes, instructor: course.value.instructor||"", cover_image_url:course.value.cover_image_url||"" });
        if (course.value.chapters && course.value.chapters.length > 0) {
          const resume=course.value.can_learn?await api.getResume(props.id):null;
          await selectChapter(course.value.chapters.find(ch=>ch.id===resume?.chapter_id)||course.value.chapters[0]);
        }
      } catch(e) { ElMessage.error(e.message); }
    };

    const selectChapter = async (ch) => {
      await saveVideo(); videoElement=null; lastVideoSave=0; courseStartTime=Date.now();
      activeChapter.value = ch; videoUrl.value = ""; docUrl.value = ""; imageUrl.value = ""; learnSeconds = 0; maxWatchedTime = 0; videoCompleted.value = false; videoDuration.value = 0;
      if (ch.content_ref_id) {
        try {
          const m = await api.getMedia(ch.content_ref_id);
          if (m) {
            // 通过统一接口获取实时可访问 URL(本地或 OSS 签名 URL)
            let url = m.file_url || "";
            try { const r = await api.getMediaUrl(m.id); url = r.url || url; } catch(e) {}
            if (ch.content_type === "video") videoUrl.value = url;
            if (ch.content_type === "document") { docUrl.value = url; docFileName.value = m.name || "文档"; if ((m.name||"").toLowerCase().endsWith(".pdf")) loadPdf(url); else { pdfDoc.value = null; pdfTotalPages.value = 0; } }
            if (ch.content_type === "image") imageUrl.value = url;
          }
        } catch(e) {}
      }
    };

    const onVideoTime = (e) => {
      videoElement=e.target;
      if(Date.now()-lastVideoSave>10000) saveVideo();
    };
    const saveVideo = async () => {
      if(videoSaving||!videoElement||activeChapter.value?.content_type!=='video'||!course.value?.can_learn||course.value.status!=='published')return;
      const ch=activeChapter.value, position=videoElement.currentTime;
      videoSaving=true;lastVideoSave=Date.now();
      try{const record=await api.updateProgress({course_id:course.value.id,chapter_id:ch.id,progress_percent:0,resume_position:{video_time:position}});chapterRecords.value=chapterRecords.value.filter(r=>r.chapter_id!==ch.id).concat(record);}catch(e){ElMessage.error('播放位置保存失败：'+e.message);}finally{videoSaving=false;}
    };
    const onVideoLoaded = (e) => {videoElement=e.target;videoDuration.value=e.target.duration||0;const saved=chapterRecords.value.find(r=>r.chapter_id===activeChapter.value.id)?.resume_position?.video_time||0;if(saved>0&&Number.isFinite(e.target.duration))e.target.currentTime=Math.min(saved,e.target.duration);};
    const completeChapter = async (ch) => {
      try {
        const elapsedSeconds = courseStartTime ? Math.round((Date.now() - courseStartTime) / 1000) : learnSeconds;
        await api.updateProgress({ course_id: props.id, chapter_id: ch.id, learning_seconds: Math.min(elapsedSeconds,86400), progress_percent: 100 });
        courseStartTime=Date.now();
        completedChapters.value.add(ch.id);
        progress.value = await api.getCourseProgress(props.id);
        ElMessage.success("章节学习完成");
      } catch(e) { ElMessage.error(e.message); }
    };
    const onVideoEnded = () => { videoCompleted.value = true; if (activeChapter.value && course.value.can_learn && course.value.status==='published') completeChapter(activeChapter.value); };
    const resetLearning = async () => {
      try {
        await ElMessageBox.confirm("重新学习后将重置当前课程的学习状态（进度、时长、完成记录），是否确定？", "重新学习确认", { type: "warning", confirmButtonText: "确定重新学习", cancelButtonText: "取消" });
        await api.resetCourseProgress(props.id);
        completedChapters.value = new Set();
        progress.value = await api.getCourseProgress(props.id);
        courseStartTime = Date.now();
        if (course.value.chapters && course.value.chapters.length > 0) selectChapter(course.value.chapters[0]);
        ElMessage.success("学习状态已重置，请重新学习");
      } catch(e) { if (e !== "cancel") ElMessage.error(e.message); }
    };

    const openEdit = () => { showEdit.value = true; };
    const doEdit = async () => { try { await api.updateCourse(props.id, editForm); ElMessage.success("保存成功"); showEdit.value = false; load(); } catch(e) { ElMessage.error(e.message); } };
    const doDelete = async () => { try { await ElMessageBox.confirm("确认删除课程？", "提示", { type: "warning" }); await api.deleteCourse(props.id); ElMessage.success("删除成功"); navigate("courses"); } catch(e) { if (e !== "cancel") ElMessage.error(e.message); } };
    const publish = async (action) => { try { let reason="";if(action==='reject'){const r=await ElMessageBox.prompt("请填写驳回原因","课程审核",{inputValidator:v=>!!v?.trim()||"原因不能为空"});reason=r.value;} await api.publishCourse(props.id, action, reason); ElMessage.success("操作成功"); load(); } catch(e) { ElMessage.error(e.message); } };

    const openAddCh = () => { chForm.title=""; chForm.content_type="video"; chForm.text_content=""; chForm.content_ref_id=""; chForm.estimated_minutes=10; chForm.is_required=true; showAddCh.value = true; };
    const doAddCh = async () => {
      if (!chForm.title) return ElMessage.warning("请输入章节标题");
      try { chForm.sort_order = (course.value.chapters||[]).length + 1; await api.addChapter(props.id, { ...chForm }); ElMessage.success("添加成功"); showAddCh.value = false; load(); } catch(e) { ElMessage.error(e.message); }
    };
    const delChapter = async (ch) => { try { await ElMessageBox.confirm("确认删除章节？", "提示", { type: "warning" }); await api.deleteChapter(props.id, ch.id); ElMessage.success("删除成功"); load(); } catch(e) { if (e !== "cancel") ElMessage.error(e.message); } };

    const openEditCh = (ch) => {
      editingChapter = ch;
      Object.assign(editChForm, { title: ch.title, content_type: ch.content_type, text_content: ch.text_content||"", content_ref_id: ch.content_ref_id||"", estimated_minutes: ch.estimated_minutes, is_required: ch.is_required });
      if (ch.content_type === "video" || ch.content_type === "document" || ch.content_type === "image") loadMedia(ch.content_type);
      showEditCh.value = true;
    };
    const doEditCh = async () => {
      if (!editChForm.title) return ElMessage.warning("请输入章节标题");
      try { await api.updateChapter(props.id, editingChapter.id, { ...editChForm }); ElMessage.success("保存成功"); showEditCh.value = false; load(); } catch(e) { ElMessage.error(e.message); }
    };

    onMounted(load);
    watch(()=>props.id,load);
    onUnmounted(() => {saveVideo();});
    const joinCourse=async()=>{try{await api.joinCourse(props.id);ElMessage.success("已加入学习");await load();}catch(e){ElMessage.error(e.message);}};
    const uploadEditCover=async(event)=>{const file=event.target.files[0];if(!file)return;try{const asset=await api.uploadMedia(file);editForm.cover_image_url=asset.file_url;ElMessage.success('封面已上传，保存后生效');}catch(e){ElMessage.error(e.message);}};
    return { saveVideo, uploadEditCover, joinCourse, course, progress, activeChapter, showEdit, showAddCh, showEditCh, canManage, completedChapters, editForm, chForm, editChForm, mediaList, selectedMediaName, videoUrl, docUrl, docFileName, imageUrl, isPdfDoc, downloadDoc, fullscreenPdf, pdfCanvas, pdfPageNum, pdfTotalPages, pdfScale, pdfLoading, pdfPrev, pdfNext, pdfZoomIn, pdfZoomOut, DIFF_MAP, STATUS_MAP, TYPE_MAP, selectChapter, onVideoTime, onVideoLoaded, onVideoEnded, videoCompleted, completeChapter, resetLearning, statusText, goExam, showExamConfig, examLinks, allExams, openExamConfig, addExamLink, removeExamLink, saveExamConfig, openEdit, doEdit, doDelete, publish, openAddCh, doAddCh, delChapter, openEditCh, doEditCh, loadMedia, onTypeChange, onEditTypeChange, navigate };
  }
};

const MyCoursesPage = {
  template: `
  <div>
    <h2 style="margin-bottom:16px">我的课程</h2>
    <el-card shadow="never">
      <template #header><span>已加入课程</span></template>
      <el-table :data="assignments" stripe>
        <el-table-column prop="course_title" label="课程名称" min-width="200" />
        <el-table-column prop="is_required" label="类型" width="80"><template #default="{row}"><el-tag :type="row.is_required?'danger':'info'" size="small">{{ row.is_required?'必修':'选修' }}</el-tag></template></el-table-column>
        <el-table-column prop="deadline" label="截止日期" width="120" />
        <el-table-column label="操作" width="100"><template #default="{row}"><el-button size="small" type="primary" @click="navigate('course/'+row.course_id)">学习</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="assignments.length===0" description="还没有加入课程，请到课程中心选择课程" />
    </el-card>
    <el-card shadow="never" style="margin-top:16px">
      <template #header><span>学习记录</span></template>
      <el-table :data="records" stripe size="small">
        <el-table-column prop="course_title" label="课程名称" min-width="200" />
        <el-table-column prop="learning_seconds" label="学习时长" width="100"><template #default="{row}">{{ Math.round((row.learning_seconds||0)/60) }}分钟</template></el-table-column>
        <el-table-column prop="progress_percent" label="进度" width="80"><template #default="{row}">{{ row.progress_percent }}%</template></el-table-column>
        <el-table-column prop="status" label="状态" width="120" />
      </el-table>
    </el-card>
  </div>`,
  setup() {
    const assignments = ref([]); const records = ref([]);
    onMounted(async () => {
      try { const [a, r] = await Promise.all([api.getMyAssignments(), api.getMyRecords()]); assignments.value = a || []; records.value = r || []; } catch(e) { ElMessage.error(e.message); }
    });
    return { assignments, records, navigate };
  }
};


// ===== Question Bank =====
const QuestionBankPage = {
  template: `
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>\u9898\u5e93\u7ba1\u7406</h2>
      <el-button type="primary" @click="showBankCreate=true">\u65b0\u5efa\u9898\u5e93</el-button>
    </div>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="never">
          <template #header><span>\u9898\u5e93\u5217\u8868</span></template>
          <div style="max-height:600px;overflow-y:auto">
            <div v-for="b in banks" :key="b.id" @click="selectBank(b)"
              :style="{padding:'12px',borderRadius:'8px',marginBottom:'8px',cursor:'pointer',
              background: selectedBank&&selectedBank.id===b.id?'#f3edff':'#fff',
              border: selectedBank&&selectedBank.id===b.id?'1px solid #7c3aed':'1px solid #ebeef5'}">
              <div style="font-weight:500;margin-bottom:4px">{{ b.name }}</div>
              <div style="font-size:13px;color:#909399">{{ b.question_count }}\u9898</div>
              <div v-if="b.description" style="font-size:12px;color:#c0c4cc;margin-top:4px">{{ b.description }}</div>
              <div style="margin-top:8px;display:flex;gap:4px" v-if="selectedBank&&selectedBank.id===b.id">
                <el-button size="small" text type="primary" @click.stop="editBank(b)">\u7f16\u8f91</el-button>
                <el-button size="small" text type="danger" @click.stop="delBank(b)">\u5220\u9664</el-button>
              </div>
            </div>
            <el-empty v-if="banks.length===0" description="\u6682\u65e0\u9898\u5e93" :image-size="60" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="18">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>{{ selectedBank ? selectedBank.name + ' (\u5171' + total + '\u9898)' : '\u8bf7\u9009\u62e9\u5de6\u4fa7\u9898\u5e93' }}</span>
              <div v-if="selectedBank">
                <el-button size="small" type="primary" @click="openQuestion()">\u65b0\u5efa\u9898\u76ee</el-button>
              </div>
            </div>
          </template>
          <div v-if="selectedBank">
            <el-input v-model="searchKw" placeholder="\u641c\u7d22\u9898\u5e72" size="small" style="width:200px;margin-bottom:12px" clearable @input="loadQuestions" />
            <el-table :data="filteredQuestions" stripe size="small">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="content" label="\u9898\u5e72" min-width="250" show-overflow-tooltip />
              <el-table-column prop="question_type" label="\u7c7b\u578b" width="80"><template #default="{row}">{{ TYPE_TXT[row.question_type] }}</template></el-table-column>
              <el-table-column prop="difficulty" label="\u96be\u5ea6" width="80"><template #default="{row}">{{ '\u2605'.repeat(row.difficulty) }}</template></el-table-column>
              <el-table-column prop="score" label="\u5206\u503c" width="70" />
              <el-table-column prop="knowledge_point" label="\u77e5\u8bc6\u70b9" width="100" show-overflow-tooltip />
              <el-table-column label="\u64cd\u4f5c" width="130"><template #default="{row}"><el-button size="small" text @click="openQuestion(row)">编辑</el-button><el-button size="small" type="danger" text @click="delQuestion(row)">\u5220\u9664</el-button></template></el-table-column>
            </el-table>
            <el-pagination v-if="total>0" :total="total" :page-size="pageSize" v-model:current-page="page" layout="prev,pager,next" @current-change="loadQuestions" style="margin-top:16px" />
          </div>
          <el-empty v-else description="\u8bf7\u70b9\u51fb\u5de6\u4fa7\u9898\u5e93\u67e5\u770b\u9898\u76ee" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="showBankCreate" :title="editingBankId?'\u7f16\u8f91\u9898\u5e93':'\u65b0\u5efa\u9898\u5e93'" width="500px">
      <el-form :model="bankForm" label-position="top">
        <el-form-item label="\u9898\u5e93\u540d\u79f0"><el-input v-model="bankForm.name" /></el-form-item>
        <el-form-item label="\u63cf\u8ff0"><el-input v-model="bankForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showBankCreate=false">\u53d6\u6d88</el-button><el-button type="primary" @click="saveBank">\u4fdd\u5b58</el-button></template>
    </el-dialog>

    <el-dialog v-model="showQCreate" :title="editingQuestion?'编辑题目':'新建题目'" width="600px">
      <el-form :model="qForm" label-position="top">
        <el-form-item label="\u9898\u578b"><el-select v-model="qForm.question_type" style="width:100%"><el-option label="\u5355\u9009\u9898" value="single_choice" /><el-option label="\u591a\u9009\u9898" value="multiple_choice" /><el-option label="\u5224\u65ad\u9898" value="true_false" /><el-option label="\u7b80\u7b54\u9898" value="short_answer" /></el-select></el-form-item>
        <el-form-item label="\u9898\u5e72"><el-input v-model="qForm.content" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="\u9009\u9879" v-if="qForm.question_type==='single_choice'||qForm.question_type==='multiple_choice'">
          <div v-for="(opt,i) in qForm.options" :key="i" style="display:flex;gap:8px;margin-bottom:8px"><el-input v-model="opt.key" style="width:60px" /><el-input v-model="opt.text" /><el-button text type="danger" @click="qForm.options.splice(i,1)">\u5220\u9664</el-button></div>
          <el-button size="small" @click="qForm.options.push({key:String.fromCharCode(65+qForm.options.length),text:''})">\u6dfb\u52a0\u9009\u9879</el-button>
        </el-form-item>
        <el-form-item :label="qForm.question_type==='short_answer'?'参考答案':'正确答案（单选填字母，多选用逗号分隔，判断填true/false）'"><el-input v-model="correctAnswerInput" /></el-form-item>
        <el-form-item label="\u96be\u5ea6"><el-rate v-model="qForm.difficulty" /></el-form-item>
        <el-form-item label="\u77e5\u8bc6\u70b9"><el-input v-model="qForm.knowledge_point" /></el-form-item>
        <el-form-item label="\u5206\u503c"><el-input-number v-model="qForm.score" :min="0.5" :step="0.5" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showQCreate=false">\u53d6\u6d88</el-button><el-button type="primary" @click="createQuestion">保存题目</el-button></template>
    </el-dialog>
  </div>`,
  setup() {
    const banks = ref([]); const selectedBank = ref(null);
    const questions = ref([]); const total = ref(0); const page = ref(1); const pageSize = 20;
    const searchKw = ref("");
    const showBankCreate = ref(false); const showQCreate = ref(false);
    const editingBankId = ref(""); const editingQuestion=ref(null);
    const bankForm = reactive({ name:"", description:"" });
    const qForm = reactive({ question_type:"single_choice", content:"", options:[{key:"A",text:""},{key:"B",text:""}], difficulty:1, knowledge_point:"", score:1 });
    const correctAnswerInput = ref("");
    const importing = ref(false);
    const TYPE_TXT = { single_choice:"\u5355\u9009", multiple_choice:"\u591a\u9009", true_false:"\u5224\u65ad", fill_blank:"\u586b\u7a7a", short_answer:"\u7b80\u7b54" };
    const filteredQuestions = computed(() => {
      if (!searchKw.value) return questions.value;
      const kw = searchKw.value.toLowerCase();
      return questions.value.filter(q => q.content.toLowerCase().includes(kw));
    });

    const loadBanks = async () => {
      try { banks.value = await api.listQuestionBanks(); } catch(e) { ElMessage.error(e.message); }
    };
    const selectBank = (b) => { selectedBank.value = b; page.value = 1; loadQuestions(); };
    const loadQuestions = async () => {
      if (!selectedBank.value) return;
      try {
        const r = await api.listQuestions({ page:page.value, page_size:pageSize, question_bank_id:selectedBank.value.id });
        questions.value = r.items||[]; total.value = r.meta.total;
      } catch(e) { ElMessage.error(e.message); }
    };
    const saveBank = async () => {
      if (!bankForm.name) return ElMessage.warning("\u8bf7\u8f93\u5165\u9898\u5e93\u540d\u79f0");
      try {
        if (editingBankId.value) {
          await api.updateQuestionBank(editingBankId.value, { name:bankForm.name, description:bankForm.description });
          ElMessage.success("\u66f4\u65b0\u6210\u529f");
        } else {
          await api.createQuestionBank({ name:bankForm.name, description:bankForm.description });
          ElMessage.success("\u521b\u5efa\u6210\u529f");
        }
        showBankCreate.value = false; editingBankId.value = ""; bankForm.name=""; bankForm.description="";
        await loadBanks();
      } catch(e) { ElMessage.error(e.message); }
    };
    const editBank = (b) => {
      editingBankId.value = b.id; bankForm.name = b.name; bankForm.description = b.description||"";
      showBankCreate.value = true;
    };
    const delBank = async (b) => {
      try {
        await ElMessageBox.confirm("\u786e\u8ba4\u5220\u9664\u9898\u5e93\u201c"+b.name+"\u201d\uff1f\u9898\u76ee\u4e0d\u4f1a\u5220\u9664\uff0c\u4f46\u4f1a\u89e3\u9664\u5173\u8054\u3002","\u63d0\u793a",{type:"warning"});
        await api.deleteQuestionBank(b.id);
        ElMessage.success("\u5220\u9664\u6210\u529f");
        if (selectedBank.value && selectedBank.value.id === b.id) { selectedBank.value = null; questions.value = []; total.value = 0; }
        await loadBanks();
      } catch(e) { if(e!=="cancel") ElMessage.error(e.message); }
    };
    const openQuestion=q=>{editingQuestion.value=q?.id||null;Object.assign(qForm,q?{question_type:q.question_type,content:q.content,options:JSON.parse(JSON.stringify(q.options||[{key:'A',text:''},{key:'B',text:''}])),difficulty:q.difficulty,knowledge_point:q.knowledge_point||'',score:q.score}:{question_type:'single_choice',content:'',options:[{key:'A',text:''},{key:'B',text:''}],difficulty:1,knowledge_point:'',score:1});correctAnswerInput.value=Array.isArray(q?.correct_answer)?q.correct_answer.join(','):q?.correct_answer||'';showQCreate.value=true;};
    const createQuestion = async () => {
      if (!qForm.content) return ElMessage.warning("\u8bf7\u8f93\u5165\u9898\u5e72");
      let answer = correctAnswerInput.value;
      if (qForm.question_type === "multiple_choice") answer = answer.split(",").map(s=>s.trim());
      try {
        const body={ ...qForm, correct_answer: answer, question_bank_id: selectedBank.value.id };
        if(editingQuestion.value)await api.updateQuestion(editingQuestion.value,body);else await api.createQuestion(body);
        ElMessage.success("\u521b\u5efa\u6210\u529f");
        showQCreate.value = false; qForm.content=""; correctAnswerInput.value=""; qForm.options=[{key:"A",text:""}];
        await loadQuestions(); await loadBanks();
      } catch(e) { ElMessage.error(e.message); }
    };
    const delQuestion = async (q) => {
      try {
        await ElMessageBox.confirm("\u786e\u8ba4\u5220\u9664\uff1f","\u63d0\u793a",{type:"warning"});
        await api.deleteQuestion(q.id);
        ElMessage.success("\u5220\u9664\u6210\u529f");
        await loadQuestions(); await loadBanks();
      } catch(e) { if(e!=="cancel") ElMessage.error(e.message); }
    };
    const handleImport = async (file) => {
      if (!selectedBank.value) return ElMessage.warning("\u8bf7\u5148\u9009\u62e9\u9898\u5e93");
      importing.value = true;
      try {
        const r = await api.importQuestions(selectedBank.value.id, file);
        let msg = "\u5bfc\u5165\u6210\u529f: " + r.imported + "\u9898";
        if (r.errors && r.errors.length) msg += "\n\u9519\u8bef: " + r.errors.join("; ");
        if (r.skipped) msg += "\n\u8df3\u8fc7: " + r.skipped + "\u884c";
        ElMessageBox.alert(msg, "\u5bfc\u5165\u7ed3\u679c", { type: r.errors.length?"warning":"success" });
        await loadQuestions(); await loadBanks();
      } catch(e) { ElMessage.error(e.message); }
      importing.value = false;
      return false;
    };
    const downloadTemplate = async () => {
      try {
        const token = api.getToken();
        const resp = await fetch(api.getQuestionBankTemplateUrl(), { headers: token ? { Authorization: "Bearer " + token } : {} });
        if (!resp.ok) throw new Error("下载失败");
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = "question_import_template.xlsx"; a.click();
        URL.revokeObjectURL(url);
      } catch(e) { ElMessage.error(e.message); }
    };

    onMounted(loadBanks);
    return { editingQuestion,openQuestion,banks, selectedBank, questions, total, page, pageSize, searchKw, showBankCreate, showQCreate, editingBankId, bankForm, qForm, correctAnswerInput, importing, TYPE_TXT, filteredQuestions, loadBanks, selectBank, loadQuestions, saveBank, editBank, delBank, createQuestion, delQuestion, handleImport, downloadTemplate, navigate };
  }
};

// ===== Exam List + Create =====

// ===== Exam Create Page =====

// ===== Practice Page (在线刷题) =====
const PracticePage = {
  template: `
  <div>
    <h2 style="margin-bottom:16px">在线刷题</h2>

    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header><span>题库分类</span></template>
          <div style="max-height:600px;overflow-y:auto">
            <div @click="selectBank('')"
              :style="{padding:'12px',borderRadius:'8px',marginBottom:'8px',cursor:'pointer',
              background: filter.question_bank_id===''?'#f3edff':'#fff',
              border: filter.question_bank_id===''?'1px solid #7c3aed':'1px solid #ebeef5'}">
              <div style="font-weight:500;margin-bottom:4px">全部题库</div>
              <div style="font-size:13px;color:#909399">{{ allQuestions.length }} 题</div>
            </div>
            <div v-for="b in bankList" :key="b.id" @click="selectBank(b.id)"
              :style="{padding:'12px',borderRadius:'8px',marginBottom:'8px',cursor:'pointer',
              background: filter.question_bank_id===b.id?'#f3edff':'#fff',
              border: filter.question_bank_id===b.id?'1px solid #7c3aed':'1px solid #ebeef5'}">
              <div style="font-weight:500;margin-bottom:4px">{{ b.name }}</div>
              <div style="font-size:13px;color:#909399">{{ b.question_count }} 题</div>
            </div>
            <div v-if="uncategorizedCount>0" @click="selectBank('__uncategorized__')"
              :style="{padding:'12px',borderRadius:'8px',marginBottom:'8px',cursor:'pointer',
              background: filter.question_bank_id==='__uncategorized__'?'#f3edff':'#fff',
              border: filter.question_bank_id==='__uncategorized__'?'1px solid #7c3aed':'1px solid #ebeef5'}">
              <div style="font-weight:500;margin-bottom:4px">未分类</div>
              <div style="font-size:13px;color:#909399">{{ uncategorizedCount }} 题</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="18">
    <el-card shadow="never" style="margin-bottom:16px" v-if="!currentQ">
      <template #header><span>选择刷题范围</span></template>
      <el-form :model="filter" label-position="top">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="题型">
              <el-select v-model="filter.question_type" clearable placeholder="全部题型" style="width:100%">
                <el-option label="单选题" value="single_choice" />
                <el-option label="多选题" value="multiple_choice" />
                <el-option label="判断题" value="true_false" />
                <el-option label="填空题" value="fill_blank" />
                <el-option label="简答题" value="short_answer" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="知识点">
              <el-select v-model="filter.knowledge_point" clearable filterable placeholder="全部知识点" style="width:100%">
                <el-option v-for="kp in knowledgePoints" :key="kp" :label="kp" :value="kp" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label=" ">
              <el-button type="primary" @click="startPractice" :disabled="!practiceList.length">开始刷题</el-button>
              <el-button v-if="errorList.length" type="warning" @click="startErrorRedo">错题重做 ({{ errorList.length }})</el-button>
              <el-button @click="loadQuestions">刷新题库</el-button>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <el-row :gutter="20" style="margin-top:8px">
        <el-col :span="6"><el-statistic title="题库总数" :value="practiceList.length" /></el-col>
        <el-col :span="6"><el-statistic title="已答题数" :value="answeredIds.size" /></el-col>
        <el-col :span="6"><el-statistic title="剩余题数" :value="Math.max(0, practiceList.length - answeredIds.size)" /></el-col>
        <el-col :span="6"><el-statistic title="错题数" :value="errorList.length" :value-style="{color: errorList.length?'#f56c6c':'#909399'}" /></el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" v-if="currentQ">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>第 {{ qIndex+1 }} 题 <el-tag size="small" style="margin-left:8px">{{ TYPE_TXT[currentQ.question_type] }}</el-tag> <el-tag size="small" type="info" style="margin-left:4px">{{ currentQ.score }}分</el-tag>
            <span style="margin-left:16px;font-size:13px;color:#909399">已答 {{ answeredIds.size }}/{{ practiceList.length }} · 错题 {{ errorList.length }}</span>
          </span>
          <el-button size="small" @click="exitPractice">退出</el-button>
        </div>
      </template>
      <div style="padding:24px">
        <div style="font-size:16px;font-weight:bold;margin-bottom:20px;line-height:1.6">{{ currentQ.content }}</div>
        <div v-if="currentQ.question_type==='single_choice'">
          <el-radio-group v-model="userAnswer" :disabled="showAnswer">
            <el-radio v-for="opt in currentQ.options" :key="opt.key" :value="opt.key" style="display:block;margin-bottom:12px;font-size:15px">{{ opt.key }}. {{ opt.text }}</el-radio>
          </el-radio-group>
        </div>
        <div v-else-if="currentQ.question_type==='multiple_choice'">
          <el-checkbox-group v-model="userAnswerMulti" :disabled="showAnswer">
            <el-checkbox v-for="opt in currentQ.options" :key="opt.key" :value="opt.key" style="display:block;margin-bottom:12px;font-size:15px">{{ opt.key }}. {{ opt.text }}</el-checkbox>
          </el-checkbox-group>
        </div>
        <div v-else-if="currentQ.question_type==='true_false'">
          <el-radio-group v-model="userAnswer" :disabled="showAnswer">
            <el-radio value="true" style="margin-right:24px">正确</el-radio>
            <el-radio value="false">错误</el-radio>
          </el-radio-group>
        </div>
        <div v-else>
          <el-input v-model="userAnswer" type="textarea" :rows="4" placeholder="请输入答案" :disabled="showAnswer" />
        </div>

        <div v-if="showAnswer" style="margin-top:24px;padding:16px;border-radius:8px" :style="{background: isCorrect?'#f0f9eb':'#fef0f0'}">
          <div style="font-weight:bold;margin-bottom:8px">
            <el-icon :color="isCorrect?'#67c23a':'#f56c6c'"><CircleCheck v-if="isCorrect" /><CircleClose v-else /></el-icon>
            {{ isCorrect?'回答正确':'回答错误' }}
          </div>
          <div style="color:#606266">正确答案：{{ correctAnswerText }}</div>
          <div v-if="currentQ.explanation" style="color:#909399;margin-top:8px">解析：{{ currentQ.explanation }}</div>
        </div>

        <div style="margin-top:24px;display:flex;justify-content:space-between">
          <el-button @click="prevQ" :disabled="qIndex===0">上一题</el-button>
          <el-button v-if="!showAnswer" type="primary" @click="checkAnswer">确认答案</el-button>
          <el-button v-else type="primary" @click="nextQ">下一题</el-button>
        </div>
      </div>
    </el-card>
      </el-col>
    </el-row>
  </div>`,
  setup() {
    const filter = reactive({ question_bank_id:"", question_type:"", knowledge_point:"" });
    const allQuestions = ref([]); const practiceList = ref([]);
    const currentQ = ref(null); const qIndex = ref(0);
    const userAnswer = ref(""); const userAnswerMulti = ref([]);
    const showAnswer = ref(false); const isCorrect = ref(false);
    const knowledgePoints = ref([]);
    const banks = ref([]);
    // 仅展示包含已加载题目的题库，题目数从已加载题目统计（与左侧错题集样式一致）
    const bankList = computed(() => banks.value
      .map(b => ({ id: b.id, name: b.name, question_count: allQuestions.value.filter(q => q.question_bank_id === b.id).length }))
      .filter(b => b.question_count > 0));
    const uncategorizedCount = computed(() => allQuestions.value.filter(q => !q.question_bank_id).length);
    const selectBank = (id) => { filter.question_bank_id = id; };
    const answeredIds = ref(new Set()); const errorList = ref([]);
    const isErrorRedo = ref(false);
    const TYPE_TXT = { single_choice:"单选题", multiple_choice:"多选题", true_false:"判断题", fill_blank:"填空题", short_answer:"简答题" };
    const correctAnswerText = computed(() => {
      if (!currentQ.value) return "";
      const a = currentQ.value.correct_answer;
      if (typeof a === "string") return a;
      if (Array.isArray(a)) return a.join(", ");
      return JSON.stringify(a);
    });

    const loadQuestions = async () => {
      try {
        banks.value = await api.listQuestionBanks().catch(() => []);
        // 分页拉取全部题目，确保覆盖所有题库，使左侧分类准确
        const all = [];
        let page = 1;
        let total = Infinity;
        while (all.length < total) {
          const r = await api.listQuestions({ page: page, page_size: 500 });
          const items = r.items || [];
          total = (r.meta && r.meta.total) || all.length + items.length;
          all.push(...items);
          if (items.length === 0) break;
          page++;
        }
        allQuestions.value = all;
        const kps = new Set();
        allQuestions.value.forEach(q => { if (q.knowledge_point) kps.add(q.knowledge_point); });
        knowledgePoints.value = [...kps];
        updatePracticeList();
      } catch(e) { ElMessage.error(e.message); }
    };
    const updatePracticeList = () => {
      let list = [...allQuestions.value];
      if (filter.question_bank_id) {
        list = list.filter(q => filter.question_bank_id === "__uncategorized__"
          ? !q.question_bank_id : q.question_bank_id === filter.question_bank_id);
      }
      if (filter.question_type) list = list.filter(q => q.question_type === filter.question_type);
      if (filter.knowledge_point) list = list.filter(q => q.knowledge_point === filter.knowledge_point);
      practiceList.value = list;
    };
    watch(() => [filter.question_bank_id, filter.question_type, filter.knowledge_point], updatePracticeList);

    const startPractice = () => {
      if (!practiceList.value.length) return;
      isErrorRedo.value = false;
      practiceList.value = [...practiceList.value].sort(() => Math.random() - 0.5);
      qIndex.value = 0; showAnswer.value = false;
      loadQ();
    };
    const startErrorRedo = () => {
      if (!errorList.value.length) return;
      isErrorRedo.value = true;
      practiceList.value = [...errorList.value].sort(() => Math.random() - 0.5);
      qIndex.value = 0; showAnswer.value = false;
      loadQ();
    };
    const loadQ = () => {
      currentQ.value = practiceList.value[qIndex.value];
      userAnswer.value = ""; userAnswerMulti.value = [];
      showAnswer.value = false; isCorrect.value = false;
    };
    const checkAnswer = () => {
      showAnswer.value = true;
      const correct = currentQ.value.correct_answer;
      if (currentQ.value.question_type === "multiple_choice") {
        const ansSet = new Set(userAnswerMulti.value);
        const corSet = new Set(Array.isArray(correct) ? correct : [correct]);
        isCorrect.value = ansSet.size === corSet.size && [...ansSet].every(x => corSet.has(x));
      } else if (currentQ.value.question_type === "fill_blank") {
        isCorrect.value = String(userAnswer.value).trim().toLowerCase() === String(correct).trim().toLowerCase();
      } else {
        isCorrect.value = String(userAnswer.value) === String(correct);
      }
      // Track answered
      answeredIds.value.add(currentQ.value.id);
      // Track errors
      if (!isCorrect.value) {
        if (!errorList.value.find(q => q.id === currentQ.value.id)) {
          errorList.value.push(currentQ.value);
        }
      } else {
        // Remove from error list if answered correctly (in redo mode)
        errorList.value = errorList.value.filter(q => q.id !== currentQ.value.id);
      }
    };
    const prevQ = () => { if (qIndex.value > 0) { qIndex.value--; loadQ(); } };
    const nextQ = () => {
      if (qIndex.value < practiceList.value.length - 1) { qIndex.value++; loadQ(); }
      else {
        // Finished all questions
        if (isErrorRedo.value) {
          ElMessage.success("错题重做完成！剩余错题: " + errorList.value.length);
        } else {
          ElMessage.success("全部题目已答完！错题: " + errorList.value.length);
        }
        exitPractice();
      }
    };
    const exitPractice = () => { currentQ.value = null; isErrorRedo.value = false; };

    onMounted(loadQuestions);
    return { filter, allQuestions, practiceList, currentQ, qIndex, userAnswer, userAnswerMulti, showAnswer, isCorrect, knowledgePoints, bankList, uncategorizedCount, selectBank, answeredIds, errorList, TYPE_TXT, correctAnswerText, loadQuestions, startPractice, startErrorRedo, checkAnswer, prevQ, nextQ, exitPractice };
  }
};

const MockExamPage = {
  template: `
  <div>
    <h2 style="margin-bottom:16px">模拟考试</h2>
    <el-card shadow="never" v-if="!started">
      <template #header><span>考试设置</span></template>
      <el-form :model="config" label-position="top">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="题目数量"><el-input-number v-model="config.count" :min="1" :max="50" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="考试时长(分钟)"><el-input-number v-model="config.duration" :min="5" :max="180" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="及格分(%)"><el-input-number v-model="config.passScore" :min="0" :max="100" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label=" ">
              <el-button type="primary" size="large" @click="startMock" :loading="loading" :disabled="!availableQuestions.length">开始模拟考试</el-button>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="题型筛选">
          <el-checkbox-group v-model="config.types">
            <el-checkbox value="single_choice">单选题</el-checkbox>
            <el-checkbox value="multiple_choice">多选题</el-checkbox>
            <el-checkbox value="true_false">判断题</el-checkbox>
            <el-checkbox value="fill_blank">填空题</el-checkbox>
            <el-checkbox value="short_answer">简答题</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <el-alert type="info" :closable="false" style="margin-top:8px">
        当前题库可用题目：{{ availableQuestions.length }}题。模拟考试会从中随机抽取{{ config.count }}题，答完后自动评分并显示每题对错和解析。不记入正式考试记录。
      </el-alert>
    </el-card>

    <div v-if="started && !finished">
      <el-page-header @back="cancelMock" style="margin-bottom:16px">
        <template #content><span>模拟考试 - 剩余 <span :style="{color: remaining<60?'red':'inherit'}">{{ formatTime(remaining) }}</span></span></template>
      </el-page-header>
      <el-progress :percentage="answeredCount/questions.length*100" :show-text="false" style="margin-bottom:16px" />
      <div v-for="(q,i) in questions" :key="q.id" class="exam-question">
        <div style="font-weight:bold;margin-bottom:12px">{{ i+1 }}. {{ q.content }} <el-tag size="small">{{ q.score }}分</el-tag> <el-tag size="small" type="info">{{ TYPE_TXT[q.question_type] }}</el-tag></div>
        <div v-if="q.question_type==='single_choice'"><el-radio-group v-model="answers[q.id]"><el-radio v-for="opt in q.options" :key="opt.key" :value="opt.key" style="display:block;margin-bottom:8px">{{ opt.key }}. {{ opt.text }}</el-radio></el-radio-group></div>
        <div v-else-if="q.question_type==='multiple_choice'"><el-checkbox-group v-model="multiAnswers[q.id]"><el-checkbox v-for="opt in q.options" :key="opt.key" :value="opt.key" style="display:block;margin-bottom:8px">{{ opt.key }}. {{ opt.text }}</el-checkbox></el-checkbox-group></div>
        <div v-else-if="q.question_type==='true_false'"><el-radio-group v-model="answers[q.id]"><el-radio value="true">正确</el-radio><el-radio value="false">错误</el-radio></el-radio-group></div>
        <div v-else><el-input v-model="answers[q.id]" type="textarea" :rows="3" placeholder="请输入答案" /></div>
      </div>
      <div style="text-align:center;margin-top:20px"><el-button type="primary" size="large" @click="submitMock">提交试卷</el-button></div>
    </div>

    <el-card shadow="never" v-if="finished">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>模拟考试结果</span>
          <el-button type="primary" @click="reset">再考一次</el-button>
        </div>
      </template>
      <el-row :gutter="20" style="margin-bottom:20px">
        <el-col :span="6"><div style="text-align:center;padding:16px"><div style="font-size:32px;font-weight:bold" :style="{color: passed?'#67c23a':'#f56c6c'}">{{ score }}/{{ maxScore }}</div><div style="color:#909399;margin-top:4px">得分</div></div></el-col>
        <el-col :span="6"><div style="text-align:center;padding:16px"><div style="font-size:32px;font-weight:bold">{{ correctCount }}/{{ questions.length }}</div><div style="color:#909399;margin-top:4px">答对题数</div></div></el-col>
        <el-col :span="6"><div style="text-align:center;padding:16px"><div style="font-size:32px;font-weight:bold">{{ percentage }}%</div><div style="color:#909399;margin-top:4px">得分率</div></div></el-col>
        <el-col :span="6"><div style="text-align:center;padding:16px"><div style="font-size:32px;font-weight:bold" :style="{color: passed?'#67c23a':'#f56c6c'}">{{ passed?'通过':'未通过' }}</div><div style="color:#909399;margin-top:4px">结果</div></div></el-col>
      </el-row>
      <el-divider />详情回顾
      <div v-for="(r,i) in results" :key="i" style="padding:16px;border:1px solid #ebeef5;border-radius:8px;margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-weight:bold">{{ i+1 }}. {{ r.content }}</span>
          <el-tag :type="r.correct?'success':'danger'" size="small">{{ r.correct?'正确':'错误' }}</el-tag>
        </div>
        <div style="color:#606266;margin-bottom:4px">你的答案：{{ r.userAnswer || '(未作答)' }}</div>
        <div style="color:#67c23a">正确答案：{{ r.correctAnswer }}</div>
        <div v-if="r.explanation" style="color:#909399;margin-top:4px">解析：{{ r.explanation }}</div>
      </div>
    </el-card>
  </div>`,
  setup() {
    const config = reactive({ count:10, duration:30, passScore:60, types:[] });
    const allQuestions = ref([]); const availableQuestions = ref([]);
    const started = ref(false); const finished = ref(false); const loading = ref(false);
    const questions = ref([]); const answers = reactive({}); const multiAnswers = reactive({});
    const remaining = ref(0); const results = ref([]);
    const score = ref(0); const maxScore = ref(0); const correctCount = ref(0);
    let timer = null;
    const TYPE_TXT = { single_choice:"单选", multiple_choice:"多选", true_false:"判断", fill_blank:"填空", short_answer:"简答" };
    const answeredCount = computed(() => {
      return questions.value.filter(q => {
        if (q.question_type === "multiple_choice") return (multiAnswers[q.id]||[]).length > 0;
        return answers[q.id] !== undefined && answers[q.id] !== "";
      }).length;
    });
    const percentage = computed(() => maxScore.value ? Math.round(score.value / maxScore.value * 100) : 0);
    const passed = computed(() => percentage.value >= config.passScore);
    const formatTime = (s) => { const m = Math.floor(s/60); const sec = s%60; return m+":"+String(sec).padStart(2,"0"); };

    const loadQuestions = async () => {
      try {
        const r = await api.listQuestions({ page:1, page_size:100 });
        allQuestions.value = r.items || [];
        updateAvailable();
      } catch(e) {}
    };
    const updateAvailable = () => {
      let list = [...allQuestions.value];
      if (config.types.length) list = list.filter(q => config.types.includes(q.question_type));
      availableQuestions.value = list;
    };
    watch(() => config.types, updateAvailable, { deep: true });

    const startMock = () => {
      loading.value = true;
      const pool = [...availableQuestions.value];
      // Shuffle and pick
      pool.sort(() => Math.random() - 0.5);
      const picked = pool.slice(0, Math.min(config.count, pool.length));
      if (!picked.length) { ElMessage.warning("没有可用题目"); loading.value = false; return; }
      questions.value = picked;
      picked.forEach(q => { answers[q.id] = ""; if (q.question_type === "multiple_choice") multiAnswers[q.id] = []; });
      started.value = true; finished.value = false;
      remaining.value = config.duration * 60;
      timer = setInterval(() => { remaining.value--; if (remaining.value <= 0) { clearInterval(timer); submitMock(); } }, 1000);
      loading.value = false;
    };

    const submitMock = () => {
      if (timer) clearInterval(timer);
      let totalScore = 0; let max = 0; let correct = 0;
      const rs = [];
      questions.value.forEach(q => {
        max += q.score;
        let userAns = "";
        let isCorrect = false;
        if (q.question_type === "multiple_choice") {
          userAns = (multiAnswers[q.id]||[]).sort().join(",");
          const correctArr = Array.isArray(q.correct_answer) ? q.correct_answer : [q.correct_answer];
          const correctSorted = [...correctArr].sort().join(",");
          isCorrect = userAns === correctSorted;
        } else if (q.question_type === "fill_blank") {
          userAns = answers[q.id] || "";
          isCorrect = userAns.trim().toLowerCase() === String(q.correct_answer).trim().toLowerCase();
        } else {
          userAns = answers[q.id] || "";
          isCorrect = String(userAns) === String(q.correct_answer);
        }
        if (isCorrect) { totalScore += q.score; correct++; }
        rs.push({ content: q.content, userAnswer: userAns, correctAnswer: Array.isArray(q.correct_answer) ? q.correct_answer.join(",") : q.correct_answer, correct: isCorrect, explanation: q.explanation });
      });
      score.value = totalScore; maxScore.value = max; correctCount.value = correct; results.value = rs;
      finished.value = true;
    };

    const cancelMock = () => { if (timer) clearInterval(timer); started.value = false; };
    const reset = () => { started.value = false; finished.value = false; questions.value = []; results.value = []; };

    onMounted(loadQuestions);
    onUnmounted(() => { if (timer) clearInterval(timer); });
    return { config, allQuestions, availableQuestions, started, finished, loading, questions, answers, multiAnswers, remaining, results, score, maxScore, correctCount, TYPE_TXT, answeredCount, percentage, passed, formatTime, startMock, submitMock, cancelMock, reset };
  }
};

const ExamCreatePage = {
  template: `
  <div>
    <el-page-header @back="navigate('exams')" style="margin-bottom:16px"><template #content><span style="font-size:18px;font-weight:bold">创建考试</span></template></el-page-header>
    <el-form :model="form" label-position="top" style="margin-bottom:16px">
      <el-row :gutter="20">
        <el-col :span="6"><el-form-item label="考试名称"><el-input v-model="form.title" /></el-form-item></el-col>
        <el-col :span="4"><el-form-item label="考试时长(分钟)"><el-input-number v-model="form.duration_minutes" :min="1" /></el-form-item></el-col>
        <el-col :span="4"><el-form-item label="及格分(%)"><el-input-number v-model="form.pass_score" :min="0" :max="100" /></el-form-item></el-col>
        <el-col :span="4"><el-form-item label="可考次数"><el-input-number v-model="form.max_attempts" :min="1" /></el-form-item></el-col>
        <el-col :span="3"><el-form-item label="乱序出题"><el-switch v-model="form.shuffle_questions" /></el-form-item></el-col>
        <el-col :span="3"><el-form-item label="打乱选项"><el-switch v-model="form.shuffle_options" /></el-form-item></el-col>
      </el-row>
      <el-form-item label="考试描述"><el-input v-model="form.description" type="textarea" :rows="2" style="max-width:800px" /></el-form-item>
      <el-form-item label="组卷方式">
        <el-radio-group v-model="form.question_mode">
          <el-radio-button value="manual">手动选题</el-radio-button>
          <el-radio-button value="random">随机抽题</el-radio-button>
        </el-radio-group>
        <span style="font-size:12px;color:#909399;margin-left:12px" v-if="form.question_mode==='manual'">从题库中手动挑选固定的题目</span>
        <span style="font-size:12px;color:#909399;margin-left:12px" v-else>每次开考时从所选题库随机抽取题目，每次卷面不同</span>
      </el-form-item>
    </el-form>

    <!-- 手动选题模式 -->
    <el-row :gutter="20" v-if="form.question_mode==='manual'">
      <el-col :span="12">
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>第一步：选择题库</span>
              <span style="font-size:12px;color:#909399">可跨题库选题，点击左侧题目添加</span>
            </div>
          </template>
          <div style="max-height:180px;overflow-y:auto">
            <el-radio-group v-model="selectedBankId" style="display:flex;flex-direction:column;gap:4px" @change="onSelectBank">
              <el-radio :value="'all'" style="margin-right:0">
                <span>全部题库</span>
                <span style="font-size:12px;color:#909399;margin-left:8px">({{ totalBankCount }}题)</span>
              </el-radio>
              <el-radio v-for="b in banks" :key="b.id" :value="b.id" style="margin-right:0">
                <span>{{ b.name }}</span>
                <span style="font-size:12px;color:#909399;margin-left:8px">({{ b.question_count||0 }}题)</span>
              </el-radio>
            </el-radio-group>
            <el-empty v-if="banks.length===0" description="暂无题库" :image-size="40" />
          </div>
        </el-card>
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>第二步：选择题目</span>
              <el-input v-model="searchKw" placeholder="搜索题目" size="small" style="width:200px" clearable />
            </div>
          </template>
          <div style="max-height:300px;overflow-y:auto">
            <div v-for="q in filteredQuestions" :key="q.id" style="padding:12px;border:1px solid #ebeef5;border-radius:8px;margin-bottom:8px">
              <div style="display:flex;justify-content:space-between;align-items:start">
                <div style="flex:1">
                  <div style="font-weight:500;margin-bottom:4px">{{ q.content }}</div>
                  <div>
                    <el-tag size="small">{{ TYPE_TXT[q.question_type] }}</el-tag>
                    <el-tag size="small" type="info" style="margin-left:4px">{{ q.score }}分</el-tag>
                    <el-tag size="small" type="warning" style="margin-left:4px" v-if="q.knowledge_point">{{ q.knowledge_point }}</el-tag>
                  </div>
                </div>
                <el-button size="small" type="primary" @click="addQuestion(q)" :disabled="selectedIds.has(q.id)">添加</el-button>
              </div>
            </div>
            <el-empty v-if="filteredQuestions.length===0" :description="selectedBankId==='all'?'暂无题目':'该题库暂无题目'" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>已选题目 ({{ selectedQuestions.length }}题, 总{{ totalScore }}分)</span>
              <el-button type="success" @click="doCreate" :disabled="!form.title||selectedQuestions.length===0" :loading="creating">创建考试</el-button>
            </div>
          </template>
          <div style="max-height:500px;overflow-y:auto">
            <div v-for="(q, i) in selectedQuestions" :key="q.id" style="padding:12px;border:1px solid #7c3aed;border-radius:8px;margin-bottom:8px;background:#f3edff">
              <div style="display:flex;justify-content:space-between;align-items:start">
                <div style="flex:1">
                  <div style="font-weight:500;margin-bottom:4px">{{ i+1 }}. {{ q.content }}</div>
                  <div style="display:flex;align-items:center;gap:8px;margin-top:4px">
                    <el-tag size="small">{{ TYPE_TXT[q.question_type] }}</el-tag>
                    <span style="font-size:13px;color:#606266">分值:</span>
                    <el-input-number v-model="q.score" :min="0.5" :step="0.5" size="small" style="width:100px" />
                    <el-button size="small" type="danger" text @click="removeQuestion(i)">移除</el-button>
                  </div>
                </div>
              </div>
            </div>
            <el-empty v-if="selectedQuestions.length===0" description="请从左侧选择题目" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 随机抽题模式 -->
    <el-row :gutter="20" v-else>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>选择题库并设置抽取数量</span>
              <span style="font-size:12px;color:#909399">可多选，每次开考时从各题库随机抽取</span>
            </div>
          </template>
          <div style="max-height:460px;overflow-y:auto">
            <div v-for="b in banks" :key="b.id" style="padding:12px;border:1px solid #ebeef5;border-radius:8px;margin-bottom:8px">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <div style="flex:1">
                  <div style="font-weight:500">{{ b.name }}</div>
                  <div style="font-size:12px;color:#909399">共 {{ b.question_count||0 }} 题</div>
                </div>
                <el-input-number v-model="randomRules[b.id].count" :min="0" :max="(b.question_count||100)" size="small" style="width:120px" />
                <el-tag v-if="randomRules[b.id].count>0" type="success" size="small" style="margin-left:8px">抽{{ randomRules[b.id].count }}题</el-tag>
              </div>
            </div>
            <el-empty v-if="banks.length===0" description="暂无题库，请先创建题库" :image-size="60" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>抽题配置概要</span>
              <el-button type="success" @click="doCreateRandom" :disabled="!form.title||selectedRuleCount===0" :loading="creating">创建考试</el-button>
            </div>
          </template>
          <div>
            <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px" title="每次开考时会重新随机抽取题目，导致每次考试卷面不同。" />
            <div v-if="selectedRules.length===0" style="color:#909399;text-align:center;padding:40px 0">请在左侧选择题库并设置抽取数量</div>
            <div v-for="(r, i) in selectedRules" :key="r.bank.id" style="padding:10px 0;border-bottom:1px dashed #ebeef5;display:flex;justify-content:space-between;align-items:center">
              <span>{{ i+1 }}. {{ r.bank.name }}</span>
              <span>随机抽{{ r.count }}题</span>
            </div>
            <div style="padding:12px 0;font-weight:600" v-if="selectedRules.length>0">预计共抽 {{ selectedRuleCount }} 题</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>`,
  setup() {
    const form = reactive({ title:"", description:"", duration_minutes:30, pass_score:60, max_attempts:10, shuffle_questions:false, shuffle_options:false, question_mode:"manual" });
    const banks = ref([]); const selectedBankId = ref("all");
    const allQuestions = ref([]); const bankQuestions = ref({}); const searchKw = ref("");
    const selectedQuestions = ref([]); const creating = ref(false);
    // random mode state: bankId -> {count, bank}
    const randomRules = reactive({});
    const TYPE_TXT = { single_choice:"单选", multiple_choice:"多选", true_false:"判断", fill_blank:"填空", short_answer:"简答" };
    const selectedIds = computed(() => new Set(selectedQuestions.value.map(q => q.id)));
    const currentQuestions = computed(() => {
      if (selectedBankId.value === "all") return allQuestions.value;
      return bankQuestions.value[selectedBankId.value] || [];
    });
    const filteredQuestions = computed(() => {
      let list = currentQuestions.value;
      if (searchKw.value) {
        const kw = searchKw.value.toLowerCase();
        list = list.filter(q => q.content.toLowerCase().includes(kw));
      }
      return list;
    });
    const totalBankCount = computed(() => allQuestions.value.length);
    const totalScore = computed(() => selectedQuestions.value.reduce((s, q) => s + (q.score || 0), 0));
    const selectedRules = computed(() => Object.values(randomRules).filter(r => r.count > 0));
    const selectedRuleCount = computed(() => selectedRules.value.reduce((s, r) => s + (r.count||0), 0));
    const loadBanks = async () => {
      try {
        banks.value = await api.listQuestionBanks() || [];
        banks.value.forEach(b => { if (!randomRules[b.id]) randomRules[b.id] = { count: 0, bank: b }; else randomRules[b.id].bank = b; });
      } catch(e) {}
    };
    const loadAllQuestions = async () => {
      try { const r = await api.listQuestions({ page:1, page_size:500 }); allQuestions.value = (r.items||[]).map(q => ({ ...q })); } catch(e) {}
    };
    const loadBankQuestions = async (bankId) => {
      if (bankQuestions.value[bankId]) return;
      try {
        const r = await api.listQuestions({ page:1, page_size:500, question_bank_id:bankId });
        bankQuestions.value[bankId] = (r.items||[]).map(q => ({ ...q }));
      } catch(e) {}
    };
    const onSelectBank = (val) => {
      if (val !== "all" && !bankQuestions.value[val]) loadBankQuestions(val);
    };
    const addQuestion = (q) => { selectedQuestions.value.push({ ...q, score: q.score || 1 }); };
    const removeQuestion = (i) => { selectedQuestions.value.splice(i, 1); };
    const doCreate = async () => {
      creating.value = true;
      try {
        await api.createExam({
          title: form.title, description: form.description,
          duration_minutes: form.duration_minutes, pass_score: form.pass_score,
          max_attempts: form.max_attempts, shuffle_questions: form.shuffle_questions, shuffle_options: form.shuffle_options,
          question_mode: "manual",
          question_ids: selectedQuestions.value.map(q => q.id),
        });
        ElMessage.success("创建成功");
        navigate("exams");
      } catch(e) { ElMessage.error(e.message); }
      creating.value = false;
    };
    const doCreateRandom = async () => {
      const rules = selectedRules.value.map(r => ({ question_bank_id: r.bank.id, count: r.count }));
      if (rules.length === 0) return ElMessage.warning("请选择题库并设置抽取数量");
      creating.value = true;
      try {
        await api.createExam({
          title: form.title, description: form.description,
          duration_minutes: form.duration_minutes, pass_score: form.pass_score,
          max_attempts: form.max_attempts, shuffle_questions: form.shuffle_questions, shuffle_options: form.shuffle_options,
          question_mode: "random",
          random_rules: rules,
        });
        ElMessage.success("创建成功");
        navigate("exams");
      } catch(e) { ElMessage.error(e.message); }
      creating.value = false;
    };
    onMounted(() => { loadBanks(); loadAllQuestions(); });
    return { form, banks, selectedBankId, allQuestions, searchKw, selectedQuestions, creating, TYPE_TXT, selectedIds, filteredQuestions, totalBankCount, totalScore, randomRules, selectedRules, selectedRuleCount, addQuestion, removeQuestion, doCreate, doCreateRandom, onSelectBank, navigate };
  }
};

const ExamListPage = {
  template: `
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>考试中心</h2>
      <el-button type="primary" v-if="api.hasPerm('exam:create')" @click="navigate('exam-create')">创建考试</el-button>
    </div>
    <el-card shadow="never">
      <el-table :data="exams" stripe>
        <el-table-column prop="title" label="考试名称" min-width="200" />
        <el-table-column prop="duration_minutes" label="时长(分)" width="100" />
        <el-table-column prop="pass_score" label="及格分" width="80" />
        <el-table-column prop="max_attempts" label="可考次数" width="100" />
        <el-table-column label="操作" width="180">
          <template #default="{row}">
            <el-button size="small" type="primary" @click="navigate('exam/'+row.id)">开始考试</el-button>
            <el-button size="small" @click="navigate('exam-result/'+row.id)">结果分析</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-card shadow="never" style="margin-top:16px">
      <template #header><span>我的考试记录</span></template>
      <el-table :data="records" stripe size="small">
        <el-table-column prop="exam_id" label="考试ID" min-width="120" />
        <el-table-column prop="attempt_number" label="第几次" width="80" />
        <el-table-column label="考试时间" width="170"><template #default="{row}"><span>{{ fmtDateTime(row.submitted_at) }}</span></template></el-table-column>
        <el-table-column prop="total_score" label="得分" width="80" />
        <el-table-column prop="max_score" label="满分" width="80" />
        <el-table-column label="结果" width="80"><template #default="{row}"><el-tag :type="row.is_pass?'success':'danger'" size="small">{{ row.is_pass?'通过':'未过' }}</el-tag></template></el-table-column>
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="操作" width="80"><template #default="{row}"><el-button size="small" text @click="viewResult(row)">详情</el-button></template></el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="showCreate" title="创建考试" width="600px">
      <el-form :model="form" label-position="top">
        <el-form-item label="考试名称"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="考试时长(分钟)"><el-input-number v-model="form.duration_minutes" :min="1" /></el-form-item>
        <el-form-item label="及格分"><el-input-number v-model="form.pass_score" :min="0" /></el-form-item>
        <el-form-item label="最多考试次数"><el-input-number v-model="form.max_attempts" :min="1" /></el-form-item>
        <el-form-item label="乱序出题"><el-switch v-model="form.shuffle_questions" /></el-form-item>
        <el-form-item label="打乱选项"><el-switch v-model="form.shuffle_options" /></el-form-item>
        <el-form-item label="选择题目">
          <el-select v-model="form.question_ids" multiple filterable style="width:100%">
            <el-option v-for="q in allQuestions" :key="q.id" :label="q.content.substring(0,40)" :value="q.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="doCreate">创建</el-button></template>
    </el-dialog>
    <el-dialog v-model="showResult" title="考试结果详情" width="720px">
      <div style="margin-bottom:12px;font-size:13px;color:#606266" v-if="resultRecord">
        <span>考试时间：{{ fmtDateTime(resultRecord.submitted_at) }}</span>
        <span style="margin-left:16px">得分：{{ resultRecord.total_score }} / {{ resultRecord.max_score }}</span>
        <el-tag :type="resultRecord.is_pass?'success':'danger'" size="small" style="margin-left:8px">{{ resultRecord.is_pass?'通过':'未过' }}</el-tag>
      </div>
      <div v-for="(a,i) in resultAnswers" :key="i" style="padding:12px;border:1px solid #ebeef5;border-radius:8px;margin-bottom:8px">
        <div style="font-weight:bold">{{ i+1 }}. {{ a.question_content || ('试题 ' + a.question_id) }}</div>
        <div v-if="a.options && a.options.length" style="margin-top:4px;font-size:13px;color:#606266">
          <div v-for="opt in a.options" :key="opt.key">{{ opt.key }}. {{ opt.text }}</div>
        </div>
        <div style="margin-top:6px">你的答案：<span :style="{color: a.is_correct?'#67c23a':'#f56c6c'}">{{ formatAnswer(a.answer) || '(未作答)' }}</span></div>
        <div>正确答案：<span style="color:#67c23a">{{ formatAnswer(a.correct_answer) }}</span></div>
        <div style="margin-top:4px">得分：{{ a.score }} <el-tag :type="a.is_correct?'success':'danger'" size="small">{{ a.is_correct?'正确':'错误' }}</el-tag></div>
        <div v-if="a.explanation" style="color:#909399;margin-top:4px">解析：{{ a.explanation }}</div>
        <div v-if="a.grader_comment" style="color:#909399;margin-top:4px">批语：{{ a.grader_comment }}</div>
      </div>
    </el-dialog>
  </div>`,
  setup() {
    const exams = ref([]); const records = ref([]); const showCreate = ref(false); const showResult = ref(false);
    const allQuestions = ref([]); const resultAnswers = ref([]);
    const form = reactive({ title:"", description:"", duration_minutes:30, pass_score:60, max_attempts:10, shuffle_questions:false, shuffle_options:false, question_ids:[] });
    const load = async () => { try { const [e,r] = await Promise.all([api.listExams({page:1,page_size:20}), api.getMyExamRecords()]); exams.value=e.items||[]; records.value=r||[]; } catch(e) { ElMessage.error(e.message); } };
    const loadQuestions = async () => { try { const r = await api.listQuestions({page:1,page_size:100}); allQuestions.value=r.items||[]; } catch(e) {} };
    const doCreate = async () => {
      if (!form.title) return ElMessage.warning("请输入考试名称");
      if (!form.question_ids.length) return ElMessage.warning("请选择题目");
      try { await api.createQuestion; await api.createExam(form); ElMessage.success("创建成功"); showCreate.value=false; form.title=""; form.question_ids=[]; load(); } catch(e) { ElMessage.error(e.message); }
    };
    const resultRecord = ref(null);
    const formatAnswer = (a) => {
      if (a === null || a === undefined) return "";
      if (Array.isArray(a)) return a.join(", ");
      if (typeof a === "object") return JSON.stringify(a);
      return String(a);
    };
    const viewResult = async (row) => { try { const r = await api.getExamRecord(row.id); resultAnswers.value = r.answers||[]; resultRecord.value = r; showResult.value=true; } catch(e) { ElMessage.error(e.message); } };
    onMounted(() => { load(); loadQuestions(); });
    return { exams, records, showCreate, showResult, allQuestions, resultAnswers, resultRecord, formatAnswer, form, load, doCreate, viewResult, navigate };
  }
};

// ===== Wrong Question Collection (错题集) =====
const WrongQuestionPage = {
  template: `
  <div>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="never">
          <template #header><span>题库分类</span></template>
          <div style="max-height:600px;overflow-y:auto">
            <div @click="selectBank(null)"
              :style="{padding:'12px',borderRadius:'8px',marginBottom:'8px',cursor:'pointer',
              background: selectedBankId===null?'#f3edff':'#fff',
              border: selectedBankId===null?'1px solid #7c3aed':'1px solid #ebeef5'}">
              <div style="font-weight:500;margin-bottom:4px">全部错题</div>
              <div style="font-size:13px;color:#909399">{{ allWrongQuestions.length }} 题</div>
            </div>
            <div v-for="b in bankList" :key="b.id" @click="selectBank(b.id)"
              :style="{padding:'12px',borderRadius:'8px',marginBottom:'8px',cursor:'pointer',
              background: selectedBankId===b.id?'#f3edff':'#fff',
              border: selectedBankId===b.id?'1px solid #7c3aed':'1px solid #ebeef5'}">
              <div style="font-weight:500;margin-bottom:4px">{{ b.name }}</div>
              <div style="font-size:13px;color:#909399">{{ b.wrong_count }} 题</div>
            </div>
            <div v-if="uncategorizedCount>0" @click="selectBank('__uncategorized__')"
              :style="{padding:'12px',borderRadius:'8px',marginBottom:'8px',cursor:'pointer',
              background: selectedBankId==='__uncategorized__'?'#f3edff':'#fff',
              border: selectedBankId==='__uncategorized__'?'1px solid #7c3aed':'1px solid #ebeef5'}">
              <div style="font-weight:500;margin-bottom:4px">未分类</div>
              <div style="font-size:13px;color:#909399">{{ uncategorizedCount }} 题</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="18">
        <el-card shadow="never">
          <template #header><span>{{ currentTitle }}</span></template>
          <div style="margin-bottom:12px;font-size:13px;color:#909399">汇总你在历次考试中答错的题目，共 {{ wrongQuestions.length }} 道。</div>
          <el-empty v-if="!wrongQuestions.length" description="暂无错题" />
          <div v-for="(q,i) in wrongQuestions" :key="q.question_id" style="padding:14px;border:1px solid #ebeef5;border-radius:8px;margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <div style="font-weight:bold;flex:1">{{ i+1 }}. {{ q.question_content }}</div>
              <el-tag type="danger" size="small">错 {{ q.wrong_count }} 次</el-tag>
            </div>
            <div v-if="q.options && q.options.length" style="margin-top:6px;font-size:13px;color:#606266">
              <div v-for="opt in q.options" :key="opt.key">{{ opt.key }}. {{ opt.text }}</div>
            </div>
            <div style="margin-top:8px">我的答案：<span style="color:#f56c6c">{{ formatAnswer(q.my_answer) || '(未作答)' }}</span></div>
            <div>正确答案：<span style="color:#67c23a">{{ formatAnswer(q.correct_answer) }}</span></div>
            <div v-if="q.explanation" style="color:#909399;margin-top:4px">解析：{{ q.explanation }}</div>
            <div style="color:#909399;margin-top:6px;font-size:12px">来源：{{ q.exam_title || q.exam_id }}（{{ fmtDateTime(q.exam_time) }}）</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>`,
  setup() {
    const allWrongQuestions = ref([]);
    const wrongQuestions = ref([]);
    const selectedBankId = ref(null);
    const bankList = ref([]);

    const formatAnswer = (a) => {
      if (a === null || a === undefined) return "";
      if (Array.isArray(a)) return a.join(", ");
      if (typeof a === "object") return JSON.stringify(a);
      return String(a);
    };

    const uncategorizedCount = computed(() => allWrongQuestions.value.filter(q => !q.question_bank_id).length);

    const currentTitle = computed(() => {
      if (selectedBankId.value === null) return "全部错题";
      if (selectedBankId.value === "__uncategorized__") return "未分类错题";
      const b = bankList.value.find(x => x.id === selectedBankId.value);
      return b ? (b.name + " 错题") : "错题集";
    });

    // Compute per-bank wrong question counts, only including banks that actually have wrong questions.
    const buildBankList = () => {
      const counts = {};
      for (const q of allWrongQuestions.value) {
        if (!q.question_bank_id) continue;
        counts[q.question_bank_id] = (counts[q.question_bank_id] || 0) + 1;
      }
      bankList.value = Object.keys(counts).map(id => ({
        id,
        name: allWrongQuestions.value.find(x => x.question_bank_id === id).question_bank_name || "未分类",
        wrong_count: counts[id],
      }));
    };

    const filterByBank = () => {
      if (selectedBankId.value === null) {
        wrongQuestions.value = allWrongQuestions.value;
      } else if (selectedBankId.value === "__uncategorized__") {
        wrongQuestions.value = allWrongQuestions.value.filter(q => !q.question_bank_id);
      } else {
        wrongQuestions.value = allWrongQuestions.value.filter(q => q.question_bank_id === selectedBankId.value);
      }
    };

    const selectBank = (id) => {
      selectedBankId.value = id;
      filterByBank();
    };

    const load = async () => {
      try {
        allWrongQuestions.value = await api.getWrongQuestions();
        buildBankList();
        filterByBank();
      } catch(e) { ElMessage.error(e.message); }
    };
    onMounted(load);
    return { wrongQuestions, allWrongQuestions, bankList, selectedBankId, currentTitle, uncategorizedCount, formatAnswer, selectBank };
  }
};

// ===== Exam Take with Timer =====
const ExamTakePage = {
  props: ["id"],
  template: `
  <div v-if="started">
    <el-page-header @back="navigate('course/'+exam.course_id)" style="margin-bottom:16px">
      <template #content><span>考试中 - 剩余 <span :style="{color: remaining<300?'red':'inherit'}">{{ formatTime(remaining) }}</span></span></template>
    </el-page-header>
    <el-progress :percentage="answeredCount/questions.length*100" :show-text="false" style="margin-bottom:16px" />
    <div v-for="(q,i) in questions" :key="q.id" class="exam-question">
      <div style="font-weight:bold;margin-bottom:12px">{{ i+1 }}. {{ q.content }} <el-tag size="small">{{ q.score }}分</el-tag></div>
      <div v-if="q.type==='single_choice'"><el-radio-group v-model="answers[q.id]" :disabled="remaining<=0||submitting" @change="saveAnswers"><el-radio v-for="opt in q.options" :key="opt.key" :value="opt.key" style="display:block;margin-bottom:8px">{{ opt.key }}. {{ opt.text }}</el-radio></el-radio-group></div>
      <div v-else-if="q.type==='multiple_choice'"><el-checkbox-group v-model="multiAnswers[q.id]" :disabled="remaining<=0||submitting" @change="saveAnswers"><el-checkbox v-for="opt in q.options" :key="opt.key" :value="opt.key" style="display:block;margin-bottom:8px">{{ opt.key }}. {{ opt.text }}</el-checkbox></el-checkbox-group></div>
      <div v-else-if="q.type==='true_false'"><el-radio-group v-model="answers[q.id]" :disabled="remaining<=0||submitting" @change="saveAnswers"><el-radio value="true">正确</el-radio><el-radio value="false">错误</el-radio></el-radio-group></div>
      <div v-else><el-input v-model="answers[q.id]" :disabled="remaining<=0||submitting" @input="queueSave" type="textarea" :rows="3" placeholder="请输入答案" /></div>
    </div>
    <p>答案{{saveFailed?'保存失败，请重试':'修改后保存'}}；截止后按此前已保存的答案结算。刷新不会延长答题时间。</p>
    <div style="text-align:center;margin-top:20px"><el-button :disabled="remaining<=0||submitting" @click="saveAnswers">保存答案</el-button><el-button type="primary" size="large" :loading="submitting" @click="doSubmit">提交试卷</el-button></div>
  </div>
  <div v-else-if="exam" style="text-align:center;padding:60px">
    <h2>{{ exam.title }}</h2>
    <p style="color:#909399;margin:12px 0">{{ exam.description || '暂无说明' }}</p>
    <el-descriptions :column="3" border style="max-width:600px;margin:0 auto 24px">
      <el-descriptions-item label="时长">{{ exam.duration_minutes }} 分钟</el-descriptions-item>
      <el-descriptions-item label="及格分">{{ exam.pass_score }}</el-descriptions-item>
      <el-descriptions-item label="可考次数">{{ exam.max_attempts }}</el-descriptions-item>
    </el-descriptions>
    <el-button @click="navigate('course/'+exam.course_id)">返回课程</el-button><el-button type="primary" size="large" @click="start">开始考试</el-button>
  </div>`,
  setup(props) {
    const exam = ref(null); const started = ref(false); const questions = ref([]);
    const answers = reactive({}); const multiAnswers = reactive({}); const recordId = ref(""); const submitting = ref(false);
    const remaining = ref(0),saveFailed=ref(false); let timer = null,saveTimer=null,deadline=0,clockOffset=0,saving=Promise.resolve();
    const answeredCount = computed(() => { let n = 0; questions.value.forEach(q => { if (q.type === "multiple_choice") { if ((multiAnswers[q.id]||[]).length > 0) n++; } else { if (answers[q.id] && answers[q.id] !== "") n++; } }); return n; });
    const formatTime = (s) => { const m = Math.floor(s/60); const sec = s%60; return m+":"+String(sec).padStart(2,"0"); };
    onMounted(async () => { try { exam.value = await api.getExam(props.id); const records=await api.getMyExamRecords(props.id);if(records.some(r=>r.status==='in_progress'))await start(); } catch(e) { ElMessage.error(e.message); } });
    const start = async () => {
      try { const r=await api.startExam(props.id);if(r.status!=='in_progress'){ElMessage.info('该次考试已结束，请在课程内查看成绩');navigate('course/'+exam.value.course_id);return;}recordId.value=r.record_id;questions.value=r.questions;deadline=Date.parse(r.deadline_at);clockOffset=Date.parse(r.server_time)-Date.now();questions.value.forEach(q=>{const saved=(r.answers||[]).find(a=>a.question_id===q.id)?.answer;if(q.type==='multiple_choice')multiAnswers[q.id]=saved||[];else answers[q.id]=saved||'';});remaining.value=Math.max(0,Math.ceil((deadline-Date.now()-clockOffset)/1000));started.value=true;timer=setInterval(()=>{remaining.value=Math.max(0,Math.ceil((deadline-Date.now()-clockOffset)/1000));if(remaining.value<=0){clearInterval(timer);doSubmit();}},500); } catch(e) { ElMessage.error(e.message); }
    };
    const answerBody=()=>({answers:questions.value.map(q=>({question_id:q.id,answer:q.type==='multiple_choice'?(multiAnswers[q.id]||[]):answers[q.id]||null}))});
    const saveAnswers=()=>{if(!recordId.value||remaining.value<=0||submitting.value)return;const body=answerBody();saving=saving.catch(()=>{}).then(()=>api.saveExamDraft(recordId.value,body)).then(()=>{saveFailed.value=false;}).catch(e=>{saveFailed.value=true;ElMessage.error(e.message);});return saving;};
    const queueSave=()=>{clearTimeout(saveTimer);saveTimer=setTimeout(saveAnswers,400);};
    const doSubmit = async () => {
      if(submitting.value)return;if (timer) clearInterval(timer);clearTimeout(saveTimer); submitting.value=true;
      try { await saving;const r=await api.submitExam(recordId.value,answerBody());let msg='得分: '+r.total_score+' / '+r.max_score;if(r.is_pass!==null)msg+=r.is_pass?'（通过）':'（未通过）';if(r.status==='submitted')msg+='（待批改，尚无最终结论）';started.value=false;await ElMessageBox.alert(msg,'考试结果',{type:r.is_pass?'success':'info'});navigate('course/'+exam.value.course_id); } catch(e) { ElMessage.error(e.message); }
      submitting.value=false;
    };
    onUnmounted(() => { if(timer) clearInterval(timer);clearTimeout(saveTimer); });
    return { saveAnswers,queueSave,saveFailed,exam, started, questions, answers, multiAnswers, recordId, submitting, remaining, answeredCount, formatTime, start, doSubmit, navigate };
  }
};

// ===== Exam Result Analysis =====
const ExamResultPage = {
  props: ["id"],
  template: `
  <div>
    <el-page-header @back="navigate('exams')" style="margin-bottom:16px"><template #content><span>考试结果分析</span></template></el-page-header>
    <el-row :gutter="20" style="margin-bottom:20px">
      <el-col :span="6"><el-card class="stat-card" shadow="hover"><div class="num">{{ analysis.total_records }}</div><div class="label">考试人数</div></el-card></el-col>
      <el-col :span="6"><el-card class="stat-card" shadow="hover"><div class="num">{{ analysis.average_score }}</div><div class="label">平均分</div></el-card></el-col>
      <el-col :span="6"><el-card class="stat-card" shadow="hover"><div class="num">{{ analysis.pass_rate }}%</div><div class="label">通过率</div></el-card></el-col>
      <el-col :span="6"><el-card class="stat-card" shadow="hover"><div class="num">{{ Object.keys(analysis.question_error_rates||{}).length }}</div><div class="label">题目数</div></el-card></el-col>
    </el-row>
    <el-card shadow="never">
      <template #header><span>成绩分布</span></template>
      <div v-for="(v,k) in analysis.score_distribution" :key="k" style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
        <span style="width:60px">{{ k }}</span>
        <el-progress :percentage="analysis.total_records?v/analysis.total_records*100:0" :show-text="false" style="flex:1" />
        <span style="width:40px">{{ v }}人</span>
      </div>
    </el-card>
    <el-card shadow="never" style="margin-top:16px">
      <template #header><span>题目错误率</span></template>
      <div v-for="(rate,qid) in analysis.question_error_rates" :key="qid" style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
        <span style="width:120px;overflow:hidden;text-overflow:ellipsis">{{ qid.substring(0,8) }}...</span>
        <el-progress :percentage="Math.round(rate*100)" :color="rate>0.5?'#f56c6c':rate>0.3?'#e6a23c':'#67c23a'" :show-text="false" style="flex:1" />
        <span style="width:50px">{{ Math.round(rate*100) }}%</span>
      </div>
    </el-card>
  </div>`,
  setup(props) {
    const analysis = ref({});
    onMounted(async () => { try { analysis.value = await api.getExamAnalysis(props.id); } catch(e) { ElMessage.error(e.message); } });
    return { analysis, navigate };
  }
};

// ===== Training Plans =====
const TrainingPlanPage = {
  template: `
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>培训计划</h2>
      <el-button type="primary" v-if="api.hasPerm('learning:manage')" @click="showCreate=true">创建计划</el-button>
    </div>
    <el-card shadow="never">
      <el-table :data="plans" stripe>
        <el-table-column prop="name" label="计划名称" min-width="200" />
        <el-table-column prop="start_date" label="开始日期" width="120" />
        <el-table-column prop="end_date" label="结束日期" width="120" />
        <el-table-column label="课程数" width="80"><template #default="{row}">{{ row.course_ids?.length || 0 }}</template></el-table-column>
        <el-table-column prop="status" label="状态" width="80" />
        <el-table-column label="操作" width="80"><template #default="{row}"><el-button size="small" type="danger" text @click="del(row)">删除</el-button></template></el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="showCreate" title="创建培训计划" width="600px">
      <el-form :model="form" label-position="top">
        <el-form-item label="计划名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="开始日期"><el-input v-model="form.start_date" placeholder="2026-01-01" /></el-form-item>
        <el-form-item label="结束日期"><el-input v-model="form.end_date" placeholder="2026-12-31" /></el-form-item>
        <el-form-item label="选择课程"><el-select v-model="form.course_ids" multiple filterable style="width:100%"><el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="doCreate">创建</el-button></template>
    </el-dialog>
  </div>`,
  setup() {
    const plans = ref([]); const courses = ref([]); const showCreate = ref(false);
    const form = reactive({ name:"", description:"", start_date:"", end_date:"", course_ids:[] });
    const load = async () => { try { const [p,c] = await Promise.all([api.listPlans({page:1,page_size:20}), api.listCourses({page:1,page_size:100})]); plans.value=p.items||[]; courses.value=c.items||[]; } catch(e) { ElMessage.error(e.message); } };
    const doCreate = async () => { if(!form.name) return ElMessage.warning("请输入名称"); try { await api.createPlan(form); ElMessage.success("创建成功"); showCreate.value=false; form.name=""; form.course_ids=[]; load(); } catch(e) { ElMessage.error(e.message); } };
    const del = async (p) => { try { await ElMessageBox.confirm("确认删除？","提示",{type:"warning"}); await api.deletePlan(p.id); ElMessage.success("删除成功"); load(); } catch(e) { if(e!=="cancel") ElMessage.error(e.message); } };
    onMounted(load);
    return { plans, courses, showCreate, form, doCreate, del };
  }
};

// ===== Learning Paths =====
const LearningPathPage = {
  template: `
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>学习路径</h2>
      <el-button type="primary" v-if="api.hasPerm('learning:manage')" @click="showCreate=true">创建路径</el-button>
    </div>
    <el-card shadow="never">
      <el-table :data="paths" stripe>
        <el-table-column prop="name" label="路径名称" min-width="200" />
        <el-table-column prop="target_job_level" label="目标职级" width="100" />
        <el-table-column prop="target_position" label="目标岗位" width="120" />
        <el-table-column prop="deadline_days" label="完成期限(天)" width="120" />
        <el-table-column label="课程数" width="80"><template #default="{row}">{{ row.course_ids?.length || 0 }}</template></el-table-column>
        <el-table-column label="操作" width="80"><template #default="{row}"><el-button size="small" type="danger" text @click="del(row)">删除</el-button></template></el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="showCreate" title="创建学习路径" width="600px">
      <el-form :model="form" label-position="top">
        <el-form-item label="路径名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="目标职级"><el-input v-model="form.target_job_level" /></el-form-item>
        <el-form-item label="目标岗位"><el-input v-model="form.target_position" /></el-form-item>
        <el-form-item label="完成期限(天)"><el-input-number v-model="form.deadline_days" :min="1" /></el-form-item>
        <el-form-item label="选择课程"><el-select v-model="form.course_ids" multiple filterable style="width:100%"><el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="doCreate">创建</el-button></template>
    </el-dialog>
  </div>`,
  setup() {
    const paths = ref([]); const courses = ref([]); const showCreate = ref(false);
    const form = reactive({ name:"", description:"", target_job_level:"", target_position:"", deadline_days:90, course_ids:[] });
    const load = async () => { try { const [p,c] = await Promise.all([api.listPaths({page:1,page_size:20}), api.listCourses({page:1,page_size:100})]); paths.value=p.items||[]; courses.value=c.items||[]; } catch(e) { ElMessage.error(e.message); } };
    const doCreate = async () => { if(!form.name) return ElMessage.warning("请输入名称"); try { await api.createPath(form); ElMessage.success("创建成功"); showCreate.value=false; form.name=""; form.course_ids=[]; load(); } catch(e) { ElMessage.error(e.message); } };
    const del = async (p) => { try { await ElMessageBox.confirm("确认删除？","提示",{type:"warning"}); await api.deletePath(p.id); ElMessage.success("删除成功"); load(); } catch(e) { if(e!=="cancel") ElMessage.error(e.message); } };
    onMounted(load);
    return { paths, courses, showCreate, form, doCreate, del };
  }
};

// ===== Course Assignment =====
const AssignmentPage = {
  template: `
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>课程分配</h2>
      <el-button type="primary" @click="openCreate">分配课程</el-button>
    </div>
    <el-card shadow="never">
      <el-table :data="assignments" stripe>
        <el-table-column label="课程" min-width="200"><template #default="{row}">{{ courseName(row.course_id) }}</template></el-table-column>
        <el-table-column label="分配类型" width="100"><template #default="{row}">{{ TYPE_TXT[row.assignment_type] }}</template></el-table-column>
        <el-table-column label="目标" min-width="150"><template #default="{row}">{{ targetName(row) }}</template></el-table-column>
        <el-table-column prop="is_required" label="必修" width="80"><template #default="{row}"><el-tag :type="row.is_required?'danger':'info'" size="small">{{ row.is_required?'是':'否' }}</el-tag></template></el-table-column>
        <el-table-column prop="deadline" label="截止日期" width="120" />
      </el-table>
    </el-card>
    <el-dialog v-model="showCreate" title="分配课程" width="600px">
      <el-form :model="form" label-position="top">
        <el-form-item label="选择课程">
          <el-select v-model="form.course_id" filterable placeholder="搜索课程" style="width:100%">
            <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="分配类型">
          <el-radio-group v-model="form.assignment_type" @change="onTypeChange">
            <el-radio-button value="user">指定用户</el-radio-button>
            <el-radio-button value="department">按部门</el-radio-button>
            <el-radio-button value="job_level">按职级</el-radio-button>
            <el-radio-button value="position">按岗位</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="选择目标" v-if="form.assignment_type==='user'">
          <el-select v-model="form.target_id" filterable placeholder="搜索用户" style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.full_name+' ('+u.username+')'" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择职级" v-if="form.assignment_type==='job_level'">
          <el-select v-model="form.target_id" filterable allow-create placeholder="选择职级" style="width:100%">
            <el-option v-for="lv in jobLevels" :key="lv" :label="lv" :value="lv" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择岗位" v-if="form.assignment_type==='position'">
          <el-select v-model="form.target_id" filterable allow-create placeholder="选择岗位" style="width:100%">
            <el-option v-for="pos in positions" :key="pos" :label="pos" :value="pos" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门ID" v-if="form.assignment_type==='department'">
          <el-input v-model="form.target_id" placeholder="输入部门ID" />
        </el-form-item>
        <el-form-item label="截止日期"><el-input v-model="form.deadline" placeholder="2026-12-31" /></el-form-item>
        <el-form-item label="必修"><el-switch v-model="form.is_required" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="doCreate">分配</el-button></template>
    </el-dialog>
  </div>`,
  setup() {
    const assignments = ref([]); const courses = ref([]); const users = ref([]);
    const jobLevels = ref([]); const positions = ref([]); const showCreate = ref(false);
    const TYPE_TXT = { user:"指定用户", department:"按部门", job_level:"按职级", position:"按岗位" };
    const form = reactive({ course_id:"", assignment_type:"user", target_id:"", deadline:"", is_required:true });
    const courseName = (id) => { const c = courses.value.find(x => x.id === id); return c ? c.title : id.substring(0,8)+"..."; };
    const targetName = (row) => {
      if (row.assignment_type === "user") { const u = users.value.find(x => x.id === row.target_id); return u ? u.full_name : row.target_id.substring(0,8)+"..."; }
      return row.target_id;
    };
    const onTypeChange = () => { form.target_id = ""; };
    const load = async () => {
      try {
        const [a, c, u] = await Promise.all([api.listAssignments({page:1,page_size:50}), api.listCourses({page:1,page_size:100}), api.listUsers({page:1,page_size:100})]);
        assignments.value = a.items||[]; courses.value = c.items||[]; users.value = u.items||[];
        const lvs = new Set(); const pos = new Set();
        users.value.forEach(u => { if (u.job_level) lvs.add(u.job_level); if (u.position) pos.add(u.position); });
        jobLevels.value = [...lvs]; positions.value = [...pos];
      } catch(e) { ElMessage.error(e.message); }
    };
    const openCreate = () => { form.course_id=""; form.assignment_type="user"; form.target_id=""; form.deadline=""; form.is_required=true; showCreate.value=true; };
    const doCreate = async () => {
      if (!form.course_id || !form.target_id) return ElMessage.warning("请选择课程和目标");
      try { await api.createAssignment(form); ElMessage.success("分配成功"); showCreate.value=false; form.target_id=""; load(); } catch(e) { ElMessage.error(e.message); }
    };
    onMounted(load);
    return { assignments, courses, users, jobLevels, positions, showCreate, TYPE_TXT, form, courseName, targetName, onTypeChange, openCreate, doCreate };
  }
};

const UserManagePage = {
  template: `<div><h2>用户管理与教师审核</h2><div style="display:flex;gap:12px;margin:16px 0">
    <el-input v-model="keyword" placeholder="搜索姓名或用户名" @keyup.enter="search" style="width:240px" />
    <el-select v-model="reviewStatus" placeholder="全部审核状态" clearable @change="search" style="width:180px"><el-option label="待审核教师" value="pending"/><el-option label="已通过教师" value="approved"/><el-option label="已驳回教师" value="rejected"/></el-select>
    <el-button @click="search">搜索</el-button><el-button type="primary" @click="openCreate">创建用户</el-button>
    </div><el-table :data="users" stripe>
    <el-table-column prop="username" label="用户名"/><el-table-column prop="full_name" label="姓名"/><el-table-column prop="email" label="邮箱"/>
    <el-table-column label="角色"><template #default="{row}">{{row.roles.map(x=>roleText[x]||x).join('、')||'待审核教师'}}</template></el-table-column>
    <el-table-column label="审核"><template #default="{row}">{{reviewText[row.teacher_review_status]||'-'}}<div style="color:#909399">{{row.teacher_review_reason}}</div></template></el-table-column>
    <el-table-column label="状态"><template #default="{row}">{{row.status==='active'?'启用':'停用'}}</template></el-table-column>
    <el-table-column label="操作" min-width="290"><template #default="{row}">
      <el-button size="small" @click="openEdit(row)">编辑</el-button><el-button size="small" @click="openRole(row)">角色</el-button>
      <el-button size="small" @click="toggleStatus(row)">{{row.status==='active'?'停用':'启用'}}</el-button>
      <template v-if="row.requested_role==='teacher' && ['pending','rejected'].includes(row.teacher_review_status)"><el-button size="small" type="success" @click="review(row,'approve')">通过</el-button><el-button size="small" type="warning" @click="review(row,'reject')">驳回</el-button></template>
    </template></el-table-column></el-table>
    <el-pagination v-model:current-page="page" :page-size="20" :total="total" @current-change="load" layout="prev,pager,next" style="margin-top:16px"/>
    <el-dialog v-model="showForm" :title="editing?'编辑用户':'创建用户'" width="500px"><el-form label-position="top">
      <el-form-item label="用户名" v-if="!editing"><el-input v-model="form.username"/></el-form-item>
      <el-form-item label="姓名"><el-input v-model="form.full_name"/></el-form-item><el-form-item label="邮箱"><el-input v-model="form.email"/></el-form-item>
      <el-form-item label="初始密码" v-if="!editing"><el-input v-model="form.password" type="password" show-password/></el-form-item>
      <el-form-item label="角色" v-if="!editing"><el-select v-model="form.role_code"><el-option v-for="(text,code) in roleText" :key="code" :label="text" :value="code"/></el-select></el-form-item>
    </el-form><template #footer><el-button @click="showForm=false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template></el-dialog>
    <el-dialog v-model="showRole" title="分配角色" width="400px"><el-select v-model="selectedRole"><el-option v-for="(text,code) in roleText" :key="code" :label="text" :value="code"/></el-select><p>分配教师角色即表示管理员已审核通过。</p><template #footer><el-button @click="showRole=false">取消</el-button><el-button type="primary" @click="saveRole">确定</el-button></template></el-dialog>
  </div>`,
  setup(){
    const users=ref([]),total=ref(0),page=ref(1),keyword=ref(''),reviewStatus=ref(''),showForm=ref(false),editing=ref(null),showRole=ref(false),selectedRole=ref('student');let roleUser=null;
    const form=reactive({username:'',full_name:'',email:'',password:'',role_code:'student'});
    const roleText={student:'学生',teacher:'教师',admin:'管理员'},reviewText={pending:'待审核',approved:'已通过',rejected:'已驳回'};
    const load=async()=>{try{const q={page:page.value,page_size:20};if(keyword.value)q.keyword=keyword.value;if(reviewStatus.value)q.review_status=reviewStatus.value;const r=await api.listUsers(q);users.value=r.items;total.value=r.meta.total;}catch(e){ElMessage.error(e.message);}};
    const search=()=>{page.value=1;load();};
    const openCreate=()=>{editing.value=null;Object.assign(form,{username:'',full_name:'',email:'',password:'',role_code:'student'});showForm.value=true;};
    const openEdit=row=>{editing.value=row;Object.assign(form,{full_name:row.full_name,email:row.email});showForm.value=true;};
    const save=async()=>{try{if(editing.value)await api.updateUser(editing.value.id,{full_name:form.full_name,email:form.email});else await api.createUser({...form});showForm.value=false;form.password='';ElMessage.success('保存成功');await load();}catch(e){ElMessage.error(e.message);}};
    const review=async(row,decision)=>{try{let reason='';if(decision==='reject'){const r=await ElMessageBox.prompt('请填写驳回原因','教师审核',{inputValidator:v=>!!v?.trim()||'原因不能为空'});reason=r.value;}await api.reviewTeacher(row.id,{decision,reason});ElMessage.success('审核完成');await load();}catch(e){if(e?.message)ElMessage.error(e.message);}};
    const toggleStatus=async row=>{try{await api.setUserStatus(row.id,{status:row.status==='active'?'inactive':'active'});await load();}catch(e){ElMessage.error(e.message);}};
    const openRole=row=>{roleUser=row;selectedRole.value=row.roles[0]||'student';showRole.value=true;};
    const saveRole=async()=>{try{await api.assignRole(roleUser.id,{role_code:selectedRole.value});showRole.value=false;await load();}catch(e){ElMessage.error(e.message);}};
    onMounted(load);return{users,total,page,keyword,reviewStatus,showForm,editing,showRole,selectedRole,form,roleText,reviewText,load,search,openCreate,openEdit,save,review,toggleStatus,openRole,saveRole};
  }
};

// ===== Org Config (job levels / positions / departments) =====
const OrgConfigPage = {
  template: `
  <div>
    <h2 style="margin-bottom:16px">组织配置</h2>
    <el-tabs v-model="tab">
      <el-tab-pane label="职级" name="job_levels">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>职级管理</span>
              <el-button type="primary" size="small" @click="openCreate('job_levels')">新增职级</el-button>
            </div>
          </template>
          <el-table :data="jobLevels" stripe>
            <el-table-column prop="name" label="职级名称" />
            <el-table-column prop="sort_order" label="排序" width="80" />
            <el-table-column prop="status" label="状态" width="100"><template #default="{row}"><el-tag :type="row.status==='active'?'success':'info'" size="small">{{ row.status }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{row}"><el-button size="small" text type="primary" @click="openEdit('job_levels', row)">编辑</el-button><el-button size="small" text type="danger" @click="del('job_levels', row)">删除</el-button></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="岗位" name="positions">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>岗位管理</span>
              <el-button type="primary" size="small" @click="openCreate('positions')">新增岗位</el-button>
            </div>
          </template>
          <el-table :data="positions" stripe>
            <el-table-column prop="name" label="岗位名称" />
            <el-table-column prop="sort_order" label="排序" width="80" />
            <el-table-column prop="status" label="状态" width="100"><template #default="{row}"><el-tag :type="row.status==='active'?'success':'info'" size="small">{{ row.status }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{row}"><el-button size="small" text type="primary" @click="openEdit('positions', row)">编辑</el-button><el-button size="small" text type="danger" @click="del('positions', row)">删除</el-button></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="部门" name="departments">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>部门管理</span>
              <el-button type="primary" size="small" @click="openCreate('departments')">新增部门</el-button>
            </div>
          </template>
          <el-table :data="departments" stripe>
            <el-table-column prop="name" label="部门名称" />
            <el-table-column prop="sort_order" label="排序" width="80" />
            <el-table-column prop="status" label="状态" width="100"><template #default="{row}"><el-tag :type="row.status==='active'?'success':'info'" size="small">{{ row.status }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{row}"><el-button size="small" text type="primary" @click="openEdit('departments', row)">编辑</el-button><el-button size="small" text type="danger" @click="del('departments', row)">删除</el-button></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
    <el-dialog v-model="showDialog" :title="editing?'编辑':'新增'" width="400px">
      <el-form label-position="top">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
  </div>`,
  setup() {
    const tab = ref("job_levels");
    const jobLevels = ref([]); const positions = ref([]); const departments = ref([]);
    const showDialog = ref(false); const editing = ref(false); const editingId = ref(null); const currentType = ref("job_levels");
    const form = reactive({ name:"", sort_order:0 });

    const API = {
      job_levels: { create: b => api.createJobLevel(b), update: (i,b) => api.updateJobLevel(i,b), del: i => api.deleteJobLevel(i) },
      positions: { create: b => api.createPosition(b), update: (i,b) => api.updatePosition(i,b), del: i => api.deletePosition(i) },
      departments: { create: b => api.createDepartment(b), update: (i,b) => api.updateDepartment(i,b), del: i => api.deleteDepartment(i) },
    };

    const load = async () => {
      try {
        const [jl, po, dp] = await Promise.all([api.listJobLevels(), api.listPositions(), api.listDepartments()]);
        jobLevels.value = jl || []; positions.value = po || []; departments.value = dp || [];
      } catch(e) { ElMessage.error(e.message); }
    };
    const openCreate = (type) => { currentType.value = type; editing.value = false; editingId.value = null; form.name=""; form.sort_order=0; showDialog.value = true; };
    const openEdit = (type, row) => { currentType.value = type; editing.value = true; editingId.value = row.id; form.name = row.name; form.sort_order = row.sort_order||0; showDialog.value = true; };
    const save = async () => {
      if (!form.name) return ElMessage.warning("请输入名称");
      const m = API[currentType.value];
      try {
        if (editing.value) { await m.update(editingId.value, { name: form.name, sort_order: form.sort_order }); }
        else { await m.create({ name: form.name, sort_order: form.sort_order }); }
        ElMessage.success("保存成功"); showDialog.value = false; load();
      } catch(e) { ElMessage.error(e.message); }
    };
    const del = async (type, row) => {
      const m = API[type];
      try { await ElMessageBox.confirm("确认删除？", "提示", { type: "warning" }); await m.del(row.id); ElMessage.success("删除成功"); load(); } catch(e) { if (e !== "cancel") ElMessage.error(e.message); }
    };
    onMounted(load);
    return { tab, jobLevels, positions, departments, showDialog, editing, form, openCreate, openEdit, save, del };
  }
};

const MediaPage = {
  template: `
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>\u7d20\u6750\u5e93</h2>
      <el-button type="primary" v-if="api.hasRole('admin')" @click="showCatCreate=true">\u65b0\u5efa\u5206\u7c7b</el-button>
    </div>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="never">
          <template #header><span>\u5206\u7c7b\u5217\u8868</span></template>
          <div style="max-height:600px;overflow-y:auto">
            <div v-for="c in categories" :key="c.id" @click="selectCategory(c)"
              :style="{padding:'12px',borderRadius:'8px',marginBottom:'8px',cursor:'pointer',
              background: selectedCat&&selectedCat.id===c.id?'#f3edff':'#fff',
              border: selectedCat&&selectedCat.id===c.id?'1px solid #7c3aed':'1px solid #ebeef5'}">
              <div style="font-weight:500;margin-bottom:4px">{{ c.name }}</div>
              <div style="font-size:13px;color:#909399">{{ c.asset_count }}\u4e2a\u7d20\u6750</div>
              <div v-if="c.description" style="font-size:12px;color:#c0c4cc;margin-top:4px">{{ c.description }}</div>
              <div style="margin-top:8px;display:flex;gap:4px" v-if="api.hasRole('admin')&&selectedCat&&selectedCat.id===c.id">
                <el-button size="small" text type="primary" @click.stop="editCategory(c)">\u7f16\u8f91</el-button>
                <el-button size="small" text type="danger" @click.stop="delCategory(c)">\u5220\u9664</el-button>
              </div>
            </div>
            <el-empty v-if="categories.length===0" description="\u6682\u65e0\u5206\u7c7b" :image-size="60" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="18">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>{{ selectedCat ? selectedCat.name + ' (\u5171' + total + '\u4e2a\u7d20\u6750)' : '\u5168\u90e8\u7d20\u6750 (' + total + ')' }}</span>
              <div v-if="selectedCat" style="display:flex;align-items:center;gap:8px">
                <el-upload :show-file-list="false" :http-request="doUpload" :before-upload="checkUpload" :disabled="uploading" :accept="'.pdf,.mp4,.avi,.mov,.jpg,.png,.mp3,.wav'">
                  <el-button size="small" type="primary" :loading="uploading">\u4e0a\u4f20\u7d20\u6750</el-button>
                </el-upload>
                <template v-if="uploading">
                  <el-progress type="line" :percentage="uploadPercent" :stroke-width="10" style="width:140px" />
                  <span style="font-size:12px;color:#909399">{{ uploadPhase==='save' ? '\u6b63\u5728\u4fdd\u5b58...' : '\u4e0a\u4f20\u4e2d...' }}</span>
                </template>
              </div>
            </div>
          </template>
          <el-input v-if="selectedCat" v-model="searchKw" placeholder="\u641c\u7d22\u7d20\u6750\u540d\u79f0" size="small" style="width:200px;margin-bottom:12px" clearable @input="load" />
          <el-table :data="items" stripe size="small">
            <el-table-column prop="name" label="\u6587\u4ef6\u540d" min-width="200" show-overflow-tooltip />
            <el-table-column prop="media_type" label="\u7c7b\u578b" width="80" />
            <el-table-column prop="file_size" label="\u5927\u5c0f" width="90"><template #default="{row}">{{ formatSize(row.file_size) }}</template></el-table-column>
            <el-table-column prop="description" label="\u63cf\u8ff0" min-width="120" show-overflow-tooltip />
            <el-table-column prop="created_at" label="\u4e0a\u4f20\u65f6\u95f4" width="170"><template #default="{row}">{{ fmtDateTime(row.created_at) }}</template></el-table-column>
            <el-table-column label="\u64cd\u4f5c" width="70"><template #default="{row}"><el-button size="small" type="danger" text @click="del(row)">\u5220\u9664</el-button></template></el-table-column>
          </el-table>
          <el-empty v-if="items.length===0" description="\u6682\u65e0\u7d20\u6750" />
          <el-pagination v-if="total>0" :total="total" :page-size="pageSize" v-model:current-page="page" layout="prev,pager,next" @current-change="load" style="margin-top:16px" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="showCatCreate" :title="editingCatId?'\u7f16\u8f91\u5206\u7c7b':'\u65b0\u5efa\u5206\u7c7b'" width="500px">
      <el-form :model="catForm" label-position="top">
        <el-form-item label="\u5206\u7c7b\u540d\u79f0"><el-input v-model="catForm.name" /></el-form-item>
        <el-form-item label="\u63cf\u8ff0"><el-input v-model="catForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCatCreate=false">\u53d6\u6d88</el-button><el-button type="primary" @click="saveCategory">\u4fdd\u5b58</el-button></template>
    </el-dialog>
  </div>`,
  setup() {
    const categories = ref([]); const selectedCat = ref(null);
    const items = ref([]); const total = ref(0); const page = ref(1); const pageSize = 20;
    const searchKw = ref("");
    const showCatCreate = ref(false); const editingCatId = ref("");
    const catForm = reactive({ name:"", description:"" });
    const uploading = ref(false); const uploadPercent = ref(0); const uploadPhase = ref("upload"); // upload=上传中 save=后端处理中
    const formatSize = (b) => { if(!b) return "-"; if(b<1024) return b+"B"; if(b<1024*1024) return (b/1024).toFixed(1)+"KB"; return (b/1024/1024).toFixed(1)+"MB"; };

    const loadCategories = async () => {
      try { categories.value = await api.listMediaCategories(); } catch(e) { ElMessage.error(e.message); }
    };
    const selectCategory = (c) => { selectedCat.value = c; page.value = 1; load(); };
    const load = async () => {
      try {
        const params = { page:page.value, page_size:pageSize };
        if (selectedCat.value) { params.category_id = selectedCat.value.id; if (searchKw.value) params.keyword = searchKw.value; }
        const r = await api.listMedia(params); items.value = r.items||[]; total.value = r.meta.total;
      } catch(e) { ElMessage.error(e.message); }
    };
    const OFFICE_EXTS = ["doc","docx","ppt","pptx"];
    const checkUpload = (file) => {
      const ext = (file.name.split(".").pop()||"").toLowerCase();
      if (OFFICE_EXTS.includes(ext)) {
        ElMessage.warning("Word/PPT 不支持在线预览，请先用 Office 将文件另存为 PDF 后再上传");
        return false;
      }
      return true;
    };
    const doUpload = async (req) => {
      if (!selectedCat.value) return ElMessage.warning("\u8bf7\u5148\u9009\u62e9\u5206\u7c7b");
      uploading.value = true; uploadPercent.value = 0; uploadPhase.value = "upload";
      try {
        // 两段式进度: 传输阶段映射 0~85%, 后端处理(转存OSS等)阶段停在 85%, 完成才到 100%
        await api.uploadMedia(req.file, { category_id: selectedCat.value.id }, (p) => {
          if (p >= 100) { uploadPhase.value = "save"; uploadPercent.value = 85; }
          else { uploadPercent.value = Math.round(p * 0.85); }
        });
        uploadPhase.value = "save"; uploadPercent.value = 100;
        ElMessage.success("\u4e0a\u4f20\u6210\u529f"); load(); loadCategories();
      } catch(e) {
        ElMessage.error("\u4e0a\u4f20\u5931\u8d25\uff1a" + (e.message || "\u672a\u77e5\u9519\u8bef"));
      } finally {
        uploading.value = false;
        setTimeout(() => { uploadPercent.value = 0; }, 1500);
      }
    };
    const del = async (m) => {
      try { await ElMessageBox.confirm("\u786e\u8ba4\u5220\u9664\uff1f","\u63d0\u793a",{type:"warning"}); await api.deleteMedia(m.id); ElMessage.success("\u5220\u9664\u6210\u529f"); load(); loadCategories(); }
      catch(e) { if(e!=="cancel") ElMessage.error(e.message); }
    };
    const saveCategory = async () => {
      if (!catForm.name) return ElMessage.warning("\u8bf7\u8f93\u5165\u5206\u7c7b\u540d\u79f0");
      try {
        if (editingCatId.value) { await api.updateMediaCategory(editingCatId.value, { name:catForm.name, description:catForm.description }); ElMessage.success("\u66f4\u65b0\u6210\u529f"); }
        else { await api.createMediaCategory({ name:catForm.name, description:catForm.description }); ElMessage.success("\u521b\u5efa\u6210\u529f"); }
        showCatCreate.value = false; editingCatId.value = ""; catForm.name=""; catForm.description=""; await loadCategories();
      } catch(e) { ElMessage.error(e.message); }
    };
    const editCategory = (c) => { editingCatId.value = c.id; catForm.name = c.name; catForm.description = c.description||""; showCatCreate.value = true; };
    const delCategory = async (c) => {
      try {
        await ElMessageBox.confirm("\u786e\u8ba4\u5220\u9664\u5206\u7c7b\u201c"+c.name+"\u201d\uff1f\u7d20\u6750\u4e0d\u4f1a\u5220\u9664\uff0c\u4f46\u4f1a\u89e3\u9664\u5173\u8054\u3002","\u63d0\u793a",{type:"warning"});
        await api.deleteMediaCategory(c.id); ElMessage.success("\u5220\u9664\u6210\u529f");
        if (selectedCat.value && selectedCat.value.id === c.id) { selectedCat.value = null; items.value = []; total.value = 0; }
        await loadCategories();
      } catch(e) { if(e!=="cancel") ElMessage.error(e.message); }
    };

    onMounted(async () => { await loadCategories(); await load(); });
    return { categories, selectedCat, items, total, page, pageSize, searchKw, showCatCreate, editingCatId, catForm, formatSize, uploading, uploadPercent, uploadPhase, loadCategories, selectCategory, load, doUpload, checkUpload, del, saveCategory, editCategory, delCategory, navigate };
  }
};

// ===== Category Management =====
const CategoryPage = {
  template: `
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>分类管理</h2>
      <el-button type="primary" v-if="api.hasPerm('course:create')" @click="showCreate=true">创建分类</el-button>
    </div>
    <el-card shadow="never">
      <el-table :data="categories" row-key="id" :tree-props="{children:'children'}" default-expand-all>
        <el-table-column prop="name" label="分类名称" min-width="200" />
        <el-table-column prop="level" label="层级" width="80" />
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column prop="description" label="描述" min-width="150" />
        <el-table-column label="操作" width="80"><template #default="{row}"><el-button size="small" type="danger" text @click="del(row)">删除</el-button></template></el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="showCreate" title="创建分类" width="500px">
      <el-form :model="form" label-position="top">
        <el-form-item label="分类名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="父分类"><el-select v-model="form.parent_id" clearable style="width:100%"><el-option label="无（顶级分类）" :value="null" /><el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate=false">取消</el-button><el-button type="primary" @click="doCreate">创建</el-button></template>
    </el-dialog>
  </div>`,
  setup() {
    const categories = ref([]); const showCreate = ref(false);
    const form = reactive({ name:"", parent_id:null, description:"", sort_order:0 });
    const buildTree = (list) => {
      const map = {}; list.forEach(i => { map[i.id] = { ...i, children: [] }; });
      const tree = []; list.forEach(i => { if (i.parent_id && map[i.parent_id]) { map[i.parent_id].children.push(map[i.id]); } else { tree.push(map[i.id]); } });
      return tree;
    };
    const load = async () => { try { const r = await api.listCategories(); categories.value = buildTree(r); } catch(e) { ElMessage.error(e.message); } };
    const doCreate = async () => { if(!form.name) return ElMessage.warning("请输入名称"); try { await api.createCategory(form); ElMessage.success("创建成功"); showCreate.value=false; form.name=""; load(); } catch(e) { ElMessage.error(e.message); } };
    const del = async (c) => { try { await ElMessageBox.confirm("确认删除？","提示",{type:"warning"}); await api.deleteCategory(c.id); ElMessage.success("删除成功"); load(); } catch(e) { if(e!=="cancel") ElMessage.error(e.message); } };
    onMounted(load);
    return { categories, showCreate, form, doCreate, del };
  }
};

// ===== Notifications with detail =====
const NotificationPage = {
  template: `
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>消息中心</h2>
      <el-button @click="markAllRead">全部已读</el-button>
    </div>
    <el-card shadow="never">
      <div v-for="n in items" :key="n.id" style="padding:16px;border-bottom:1px solid #ebeef5;cursor:pointer" @click="showDetail(n)">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span :style="{fontWeight: n.is_read?'normal':'bold',fontSize:'15px'}">{{ n.title }}</span>
          <div><el-tag size="small" :type="n.is_read?'info':'danger'">{{ n.notification_type }}</el-tag><span style="font-size:12px;color:#909399;margin-left:8px">{{ fmtDateTime(n.created_at) }}</span></div>
        </div>
        <div style="margin-top:4px;color:#606266;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ n.body }}</div>
      </div>
      <el-empty v-if="items.length===0" description="暂无消息" />
    </el-card>
    <el-dialog v-model="detailVisible" :title="detail.title" width="500px">
      <div style="line-height:1.8">{{ detail.body }}</div>
      <div style="margin-top:12px;color:#909399;font-size:12px">{{ fmtDateTime(detail.created_at) }}</div>
    </el-dialog>
  </div>`,
  setup() {
    const items = ref([]); const detailVisible = ref(false); const detail = ref({});
    const load = async () => { try { const r = await api.listNotifications({page:1,page_size:50}); items.value=r.items||[]; } catch(e) { ElMessage.error(e.message); } };
    const markAllRead = async () => { try { await api.markAllRead(); ElMessage.success("已全部标记为已读"); load(); loadUnread(); } catch(e) { ElMessage.error(e.message); } };
    const showDetail = (n) => { detail.value = n; detailVisible.value = true; if(!n.is_read) { api.markRead([n.id]).then(()=>{ load(); loadUnread(); }).catch(()=>{}); } };
    onMounted(load);
    return { items, detailVisible, detail, markAllRead, showDetail };
  }
};

// ===== Profile with edit =====
const ProfilePage = {
  template:`<div><h2 style="margin-bottom:16px">个人中心</h2>
    <el-alert v-if="profile.requested_role==='teacher'" :title="'教师审核：'+(reviewText[profile.teacher_review_status]||'未审核')" :description="profile.teacher_review_reason||'审核通过后可创建和管理课程。'" :type="profile.teacher_review_status==='approved'?'success':'info'" :closable="false" style="margin-bottom:16px"/>
    <el-button @click="refreshReview" style="margin-bottom:16px">刷新审核状态</el-button>
    <el-card><el-form label-position="top" style="max-width:480px"><el-form-item label="用户名">{{profile.username}}</el-form-item>
      <el-form-item label="姓名"><el-input v-model="form.full_name"/></el-form-item><el-form-item label="邮箱"><el-input v-model="form.email"/></el-form-item><el-button type="primary" @click="save">保存资料</el-button>
    </el-form></el-card>
    <el-card style="margin-top:16px"><template #header>修改密码</template><el-form label-position="top" style="max-width:480px">
      <el-form-item label="原密码"><el-input v-model="password.old_password" type="password" show-password/></el-form-item>
      <el-form-item label="新密码"><el-input v-model="password.new_password" type="password" placeholder="至少8个字符" show-password/></el-form-item>
      <el-button @click="changePassword">修改密码并重新登录</el-button></el-form></el-card>
  </div>`,
  setup(){const profile=ref({}),form=reactive({full_name:'',email:''}),password=reactive({old_password:'',new_password:''});const reviewText={pending:'待审核',approved:'已通过',rejected:'已驳回'};
    const load=async()=>{try{profile.value=await api.getProfile();Object.assign(form,{full_name:profile.value.full_name,email:profile.value.email});}catch(e){ElMessage.error(e.message);}};
    const save=async()=>{try{await api.updateProfile({...form});await load();ElMessage.success('资料已保存');}catch(e){ElMessage.error(e.message);}};
    const refreshReview=async()=>{await api.getMe();window.location.reload();};
    const changePassword=async()=>{try{await api.changePassword({...password});api.clearToken();window.location.hash='#login';window.location.reload();}catch(e){ElMessage.error(e.message);}};
    onMounted(load);return{profile,form,password,reviewText,save,refreshReview,changePassword};}
};

// ===== Main App with full navigation =====
const App = {
  setup() {
    const currentPage = ref("login"); const currentParam = ref(null);
    const userInfo = ref(null); const sidebarCollapsed = ref(false);
    const unreadCount = computed(() => unreadState.count);
    const ALL_MENU_ITEMS = [
      {key:'dashboard',label:'工作台',icon:'HomeFilled'},
      {key:'courses',label:'课程中心',icon:'Reading',perm:'course:read'},
      {key:'my-courses',label:'我的课程',icon:'Notebook',role:'student'},
      {key:'media',label:'素材库',icon:'FolderOpened',perm:'course:create'},
      {key:'question-banks',label:'题库管理',icon:'Document',perm:'exam:create'},
      {key:'categories',label:'课程分类',icon:'Files',perm:'system:config'},
      {key:'users',label:'用户与教师审核',icon:'UserFilled',perm:'user:read'},
      {key:'notifications',label:'消息中心',icon:'Bell'},
      {key:'profile',label:'个人中心',icon:'User'},
    ];
    const menuItems=computed(()=>{userInfo.value;return ALL_MENU_ITEMS.filter(m=>(!m.perm||api.hasPerm(m.perm))&&(!m.role||api.hasRole(m.role)));});
    const parseRoute = () => { const hash = window.location.hash.replace("#","")||"dashboard"; const parts = hash.split("/"); currentPage.value=parts[0]; currentParam.value=parts[1]||null; if(api.isLoggedIn()) loadUnread(); };
    const logout = async (msg) => { try { await api.logout(); } catch(e) {} api.clearToken(); if (msg) { try { ElMessage.warning(msg); } catch(e){} } window.location.hash="#login"; window.location.reload(); };
    // Session timeout auto-logout: check JWT exp periodically (2h timeout)
    const sessionCheckTimer = ref(null);
    const startSessionTimer = () => {
      if (sessionCheckTimer.value) clearInterval(sessionCheckTimer.value);
      sessionCheckTimer.value = setInterval(() => {
        const token = api.getToken();
        if (!token) { clearInterval(sessionCheckTimer.value); return; }
        try {
          const parts = token.split(".");
          if (parts.length !== 3) { logout("\u767b\u5f55\u4f1a\u8bdd\u65e0\u6548"); return; }
          const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
          const exp = payload.exp * 1000;
          if (exp && exp < Date.now()) logout("\u767b\u5f55\u5df2\u8d85\u65f6\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55");
        } catch(e) {}
      }, 30000); // check every 30s
    };
    const componentMap={login:LoginPage,dashboard:DashboardPage,'my-courses':MyCoursesPage,courses:CourseListPage,course:CourseDetailPage,media:MediaPage,'question-banks':QuestionBankPage,exam:ExamTakePage,categories:CategoryPage,notifications:NotificationPage,users:UserManagePage,profile:ProfilePage};
    const currentComponent=computed(()=>{if(!api.isLoggedIn())return LoginPage;if(!userInfo.value)return null;const allowed=currentPage.value==='course'?api.hasPerm('course:read'):currentPage.value==='exam'?api.hasPerm('exam:read'):menuItems.value.some(m=>m.key===currentPage.value);return allowed?(componentMap[currentPage.value]||DashboardPage):DashboardPage;});
    onMounted(async () => { parseRoute(); window.addEventListener("hashchange",()=>parseRoute()); if(api.isLoggedIn()) { try { userInfo.value=await api.getMe(); loadUnread(); startSessionTimer(); } catch(e) { api.clearToken(); } } });
    const drawerVisible = ref(false);
    const handleMenuSelect = (key) => { navigate(key); if (isMobile.value) drawerVisible.value = false; };
    return { currentPage, currentParam, userInfo, unreadCount, sidebarCollapsed, menuItems, logout, currentComponent, api, sessionCheckTimer, isMobile, isTablet, drawerVisible, handleMenuSelect };
  },
  template: `
  <component :is="currentComponent" v-if="!api.isLoggedIn() || currentPage==='login'" />
  <el-container v-else class="main-layout">
    <el-drawer v-if="isMobile" v-model="drawerVisible" direction="ltr" :size="240" :with-header="false">
      <div style="background:#1e0f3f;height:100%">
        <div class="sidebar-logo">校园在线</div>
        <el-scrollbar style="height:calc(100vh - 60px)">
          <el-menu :default-active="currentPage" background-color="#1e0f3f" text-color="#ffffffa6" active-text-color="#fff" @select="handleMenuSelect">
            <el-menu-item v-for="m in menuItems" :key="m.key" :index="m.key"><el-icon><component :is="m.icon" /></el-icon><span>{{ m.label }}</span><el-badge v-if="m.key==='notifications'&&unreadCount>0" class="badge-side" :value="unreadCount" position="top-right" style="margin-left:8px" /></el-menu-item>
          </el-menu>
        </el-scrollbar>
      </div>
    </el-drawer>
    <el-aside v-if="!isMobile" :width="sidebarCollapsed?'64px':'200px'">
      <div class="sidebar-logo">{{ sidebarCollapsed?'学':'校园在线学习平台' }}</div>
      <el-scrollbar style="height:calc(100vh - 60px)">
        <el-menu :default-active="currentPage" :collapse="sidebarCollapsed" background-color="#1e0f3f" text-color="#ffffffa6" active-text-color="#fff" @select="navigate">
          <el-menu-item v-for="m in menuItems" :key="m.key" :index="m.key"><el-icon><component :is="m.icon" /></el-icon><span>{{ m.label }}</span><el-badge v-if="m.key==='notifications'&&unreadCount>0" class="badge-side" :value="unreadCount" position="top-right" style="margin-left:8px" /></el-menu-item>
        </el-menu>
      </el-scrollbar>
    </el-aside>
    <el-container>
      <el-header class="header-bar">
        <div style="display:flex;align-items:center;gap:8px"><el-button v-if="isMobile" text @click="drawerVisible=true"><el-icon size="22"><Menu /></el-icon></el-button><el-button v-else text @click="sidebarCollapsed=!sidebarCollapsed"><el-icon size="20"><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon></el-button><span v-if="!isMobile" style="font-size:16px;font-weight:500">{{ menuItems.find(m=>m.key===currentPage)?.label || '工作台' }}</span></div>
        <div style="display:flex;align-items:center;gap:12px">
          <el-badge class="badge-bell" :value="unreadCount" :hidden="unreadCount===0" position="top-right"><el-button text @click="navigate('notifications')"><el-icon size="18"><Bell /></el-icon></el-button></el-badge>
          <el-dropdown><span style="cursor:pointer;display:flex;align-items:center;gap:6px"><el-avatar size="small" style="background:#7c3aed">{{ (userInfo?.full_name||'U')[0] }}</el-avatar><span v-if="!isMobile">{{ userInfo?.full_name || 'User' }}</span></span><template #dropdown><el-dropdown-menu><el-dropdown-item @click="navigate('profile')">个人中心</el-dropdown-item><el-dropdown-item divided @click="logout">退出登录</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
        </div>
      </el-header>
      <el-main class="page-content"><component :is="currentComponent" :id="currentParam" /></el-main>
    </el-container>
  </el-container>`
};

try {
  const app = createApp(App);
  app.use(ElementPlus);
  app.config.globalProperties.navigate = navigate;
  app.config.globalProperties.api = api;
  app.config.globalProperties.$isMobile = isMobile;
  app.config.globalProperties.$isTablet = isTablet;
  // 将 ISO 时间字符串格式化为本地时间 yyyy-MM-dd HH:mm:ss（24 小时制）
  app.config.globalProperties.fmtDateTime = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    const p = (n) => String(n).padStart(2, "0");
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate())
      + " " + p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
  };
  if (typeof ElementPlusIconsVue !== "undefined") { for (const [k,c] of Object.entries(ElementPlusIconsVue)) { app.component(k,c); } }
  app.mount("#app");
} catch(e) {
  document.getElementById("app").innerHTML = '<div style="padding:40px;color:red;font-family:monospace">App Error: ' + e.message + "</div>";
}
