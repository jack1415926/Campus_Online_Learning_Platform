// Campus learning platform - Vue 3 application
const { createApp, ref, reactive, computed, onMounted, onUnmounted, watch, nextTick, shallowRef } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;
const platformState = reactive({platform_name:'校园在线学习平台',registration_open:true});
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
const TYPE_MAP = { video: "视频", document: "文档", text: "文字", image: "图片" };

// ===== Login =====
const LoginPage = {
  template: `<div class="login-container"><div class="login-card">
    <div class="login-title">{{platform.platform_name}}</div><p style="text-align:center;color:#909399">课程 · 学习 · 交流</p>
    <el-form v-if="mode==='login'" label-position="top" @submit.prevent="doLogin">
      <el-form-item label="用户名 / 邮箱"><el-input v-model="lf.username" placeholder="请输入用户名或邮箱" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="lf.password" type="password" placeholder="请输入密码" show-password /></el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">登录</el-button>
      <el-button v-if="platform.registration_open" text @click="mode='register'" style="margin-top:12px">注册新账号</el-button><p v-else style="margin-top:12px">平台暂未开放注册</p>
    </el-form>
    <el-form v-else-if="platform.registration_open" label-position="top" @submit.prevent="doRegister">
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
  template: `<div><h2 style="margin-bottom:16px">欢迎来到{{platform.platform_name}}</h2>
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
    const form = reactive({ title:"", description:"", difficulty:"beginner", estimated_minutes:60, instructor:"", cover_image_url:"" });
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
  components: { HomeworkPanel, CampusExamPanel, CommunicationPanel, CertificatePanel },
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
              <el-tag :type="progress.is_complete?'success':(statusText==='学习中'?'warning':'info')" size="small">{{ statusText }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
    <homework-panel :course="course" :key="course.id"/>
    <campus-exam-panel :course="course" :key="course.id"/>
    <communication-panel :course="course" :key="course.id"/>
    <certificate-panel :course="course" :key="course.id"/>

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
            <el-button @click="loadMedia(chForm.content_type)">刷新</el-button>
          </div>
          <div v-if="chForm.content_ref_id" style="margin-top:8px;color:#67c23a;font-size:13px">已选择: {{ selectedMediaName }}</div>
        </el-form-item>
        <el-form-item label="学时(分钟)"><el-input-number v-model="chForm.estimated_minutes" :min="0" /></el-form-item>
        <el-form-item label="顺序（数字越小越靠前）"><el-input-number v-model="chForm.sort_order" :min="0" :max="1000000" :precision="0" /></el-form-item>
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
            <el-button @click="loadMedia(editChForm.content_type)">刷新</el-button>
          </div>
        </el-form-item>
        <el-form-item label="学时(分钟)"><el-input-number v-model="editChForm.estimated_minutes" :min="0" /></el-form-item>
        <el-form-item label="顺序（数字越小越靠前）"><el-input-number v-model="editChForm.sort_order" :min="0" :max="1000000" :precision="0" /></el-form-item>
        <el-form-item label="必修"><el-switch v-model="editChForm.is_required" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showEditCh=false">取消</el-button><el-button type="primary" @click="doEditCh">保存</el-button></template>
    </el-dialog>

  </div>`,
  setup(props) {
    const course = ref(null); const progress = ref({}); const activeChapter = ref(null);
    const showEdit = ref(false); const showAddCh = ref(false); const showEditCh = ref(false);
    const canManage = ref(false); const completedChapters = ref(new Set()); let courseStartTime = null;
    const chapterRecords = ref([]); let videoElement=null, lastVideoSave=0, videoSaving=false;
    const editForm = reactive({ title:"", description:"", difficulty:"beginner", estimated_minutes:0, instructor:"" });
    const chForm = reactive({ title:"", content_type:"video", text_content:"", content_ref_id:"", estimated_minutes:10, is_required:true, sort_order:0 });
    const editChForm = reactive({ title:"", content_type:"video", text_content:"", content_ref_id:"", estimated_minutes:0, is_required:true, sort_order:0 });
    const mediaList = ref([]);
    const selectedMediaName = computed(() => { const m = mediaList.value.find(x => x.id === chForm.content_ref_id); return m ? m.name : ""; });
    const videoUrl = ref(""); const docUrl = ref(""); const docFileName = ref(""); const imageUrl = ref(""); const pdfCanvas = ref(null); let learnSeconds = 0; const videoCompleted = ref(false); const videoDuration = ref(0); const pdfDoc = shallowRef(null); const pdfPageNum = ref(1); const pdfTotalPages = ref(0); const pdfScale = ref(1.2); const pdfLoading = ref(false);
    const statusText = computed(() => {
      if (progress.value.is_complete) return "已完成";
      if (progress.value.status === "in_progress") return "学习中";
      return "未开始";
    });
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
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs-2.16.105/pdf.worker.min.js";
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
    let editingChapter = null;
    const loadMedia = async (contentType) => {
      try {
        const type = contentType || "document";
        const r = await api.listMedia({ page:1, page_size:100, media_type: type });
        let items = r.items || [];
        if (type === "document") items = items.filter(m => /\.(pdf|docx)$/i.test(m.name || ""));
        mediaList.value = items;
      } catch(e) { mediaList.value = []; ElMessage.error(e.message); }
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
      activeChapter.value = ch; videoUrl.value = ""; docUrl.value = ""; imageUrl.value = ""; learnSeconds = 0; videoCompleted.value = false; videoDuration.value = 0;
      if (ch.content_ref_id) {
        try {
          const m = await api.getMedia(ch.content_ref_id);
          if (m) {
            // 通过统一接口获取实时可访问 URL(短期鉴权链接)
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
    const openEdit = () => { showEdit.value = true; };
    const doEdit = async () => { try { await api.updateCourse(props.id, editForm); ElMessage.success("保存成功"); showEdit.value = false; load(); } catch(e) { ElMessage.error(e.message); } };
    const doDelete = async () => { try { await ElMessageBox.confirm("确认删除课程？", "提示", { type: "warning" }); await api.deleteCourse(props.id); ElMessage.success("删除成功"); navigate("courses"); } catch(e) { if (e !== "cancel") ElMessage.error(e.message); } };
    const publish = async (action) => { try { let reason="";if(action==='reject'){const r=await ElMessageBox.prompt("请填写驳回原因","课程审核",{inputValidator:v=>!!v?.trim()||"原因不能为空"});reason=r.value;} await api.publishCourse(props.id, action, reason); ElMessage.success("操作成功"); load(); } catch(e) { ElMessage.error(e.message); } };

    const openAddCh = () => { chForm.title=""; chForm.content_type="video"; chForm.text_content=""; chForm.content_ref_id=""; chForm.estimated_minutes=10; chForm.is_required=true; chForm.sort_order=Math.max(0,...(course.value?.chapters||[]).map(ch=>ch.sort_order||0))+1; showAddCh.value = true; loadMedia(chForm.content_type); };
    const doAddCh = async () => {
      if (!chForm.title) return ElMessage.warning("请输入章节标题");
      try { await api.addChapter(props.id, { ...chForm }); ElMessage.success("添加成功"); showAddCh.value = false; load(); } catch(e) { ElMessage.error(e.message); }
    };
    const delChapter = async (ch) => { try { await ElMessageBox.confirm("确认删除章节？", "提示", { type: "warning" }); await api.deleteChapter(props.id, ch.id); ElMessage.success("删除成功"); load(); } catch(e) { if (e !== "cancel") ElMessage.error(e.message); } };

    const openEditCh = (ch) => {
      editingChapter = ch;
      Object.assign(editChForm, { title: ch.title, content_type: ch.content_type, text_content: ch.text_content||"", content_ref_id: ch.content_ref_id||"", estimated_minutes: ch.estimated_minutes, is_required: ch.is_required, sort_order: ch.sort_order });
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
    return { saveVideo, uploadEditCover, joinCourse, course, progress, activeChapter, showEdit, showAddCh, showEditCh, canManage, completedChapters, editForm, chForm, editChForm, mediaList, selectedMediaName, videoUrl, docUrl, docFileName, imageUrl, isPdfDoc, downloadDoc, pdfCanvas, pdfPageNum, pdfTotalPages, pdfScale, pdfLoading, pdfPrev, pdfNext, pdfZoomIn, pdfZoomOut, DIFF_MAP, STATUS_MAP, TYPE_MAP, selectChapter, onVideoTime, onVideoLoaded, onVideoEnded, videoCompleted, completeChapter, statusText, openEdit, doEdit, doDelete, publish, openAddCh, doAddCh, delChapter, openEditCh, doEditCh, loadMedia, onTypeChange, onEditTypeChange, navigate };
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
    const TYPE_TXT = { single_choice:"\u5355\u9009", multiple_choice:"\u591a\u9009", true_false:"\u5224\u65ad", short_answer:"\u7b80\u7b54" };
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
    onMounted(loadBanks);
    return { editingQuestion,openQuestion,banks, selectedBank, questions, total, page, pageSize, searchKw, showBankCreate, showQCreate, editingBankId, bankForm, qForm, correctAnswerInput, TYPE_TXT, filteredQuestions, loadBanks, selectBank, loadQuestions, saveBank, editBank, delBank, createQuestion, delQuestion, navigate };
  }
};


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

const MediaPage = {
  template: `
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>\u7d20\u6750\u5e93</h2>
      <el-button type="primary" v-if="api.hasPerm('course:create')" @click="openCreateCategory">\u65b0\u5efa\u5206\u7c7b</el-button>
    </div>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="never">
          <template #header><span>\u5206\u7c7b\u5217\u8868</span></template>
          <div style="max-height:600px;overflow-y:auto">
            <el-button text :type="selectedCat ? 'default' : 'primary'" @click="selectCategory(null)">全部素材</el-button>
            <div v-for="c in categories" :key="c.id" @click="selectCategory(c)"
              :style="{padding:'12px',borderRadius:'8px',marginBottom:'8px',cursor:'pointer',
              background: selectedCat&&selectedCat.id===c.id?'#f3edff':'#fff',
              border: selectedCat&&selectedCat.id===c.id?'1px solid #7c3aed':'1px solid #ebeef5'}">
              <div style="font-weight:500;margin-bottom:4px">{{ c.name }}</div>
              <div style="font-size:13px;color:#909399">{{ c.asset_count }}\u4e2a\u7d20\u6750</div>
              <div v-if="c.description" style="font-size:12px;color:#c0c4cc;margin-top:4px">{{ c.description }}</div>
              <div style="margin-top:8px;display:flex;gap:4px" v-if="c.can_manage&&selectedCat&&selectedCat.id===c.id">
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
              <div style="display:flex;align-items:center;gap:8px">
                <el-upload :show-file-list="false" :http-request="doUpload" :before-upload="checkUpload" :disabled="uploading" :accept="'.pdf,.docx,.mp4,.jpg,.jpeg,.png'">
                  <el-button size="small" type="primary" :loading="uploading">\u4e0a\u4f20\u7d20\u6750</el-button>
                </el-upload>
                <template v-if="uploading">
                  <el-progress type="line" :percentage="uploadPercent" :stroke-width="10" style="width:140px" />
                  <span style="font-size:12px;color:#909399">{{ uploadPhase==='save' ? '\u6b63\u5728\u4fdd\u5b58...' : '\u4e0a\u4f20\u4e2d...' }}</span>
                </template>
              </div>
            </div>
          </template>
          <el-input v-model="searchKw" placeholder="\u641c\u7d22\u7d20\u6750\u540d\u79f0" size="small" style="width:200px;margin-bottom:12px" clearable @input="load" />
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
        if (selectedCat.value) params.category_id = selectedCat.value.id;
        if (searchKw.value) params.keyword = searchKw.value;
        const r = await api.listMedia(params); items.value = r.items||[]; total.value = r.meta.total;
      } catch(e) { ElMessage.error(e.message); }
    };
    const OFFICE_EXTS = ["doc","ppt","pptx"];
    const checkUpload = (file) => {
      const ext = (file.name.split(".").pop()||"").toLowerCase();
      if (OFFICE_EXTS.includes(ext)) {
        ElMessage.warning("Word/PPT 不支持在线预览，请先用 Office 将文件另存为 PDF 后再上传");
        return false;
      }
      return true;
    };
    const doUpload = async (req) => {
      uploading.value = true; uploadPercent.value = 0; uploadPhase.value = "upload";
      try {
        // 两段式进度: 传输阶段映射 0~85%, 后端处理阶段停在 85%, 完成才到 100%
        await api.uploadMedia(req.file, selectedCat.value ? { category_id: selectedCat.value.id } : {}, (p) => {
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
    const openCreateCategory = () => { editingCatId.value=""; catForm.name=""; catForm.description=""; showCatCreate.value=true; };
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
        await loadCategories(); await load();
      } catch(e) { if(e!=="cancel") ElMessage.error(e.message); }
    };

    onMounted(async () => { await loadCategories(); await load(); });
    return { categories, selectedCat, items, total, page, pageSize, searchKw, showCatCreate, editingCatId, catForm, formatSize, uploading, uploadPercent, uploadPhase, loadCategories, selectCategory, load, doUpload, checkUpload, del, openCreateCategory, saveCategory, editCategory, delCategory, navigate };
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
      <div><el-button @click="refresh">刷新消息</el-button><el-button @click="markAllRead">全部已读</el-button></div>
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
    <el-pagination v-if="total>20" v-model:current-page="page" :total="total" :page-size="20" @current-change="load" layout="prev,pager,next"/>
    <el-dialog v-model="detailVisible" :title="detail.title" width="500px">
      <div style="line-height:1.8">{{ detail.body }}</div>
      <div style="margin-top:12px;color:#909399;font-size:12px">{{ fmtDateTime(detail.created_at) }}</div>
      <el-button v-if="detail.extra_data?.course_id" type="primary" style="margin-top:12px" @click="follow">打开对应课程内容</el-button>
    </el-dialog>
  </div>`,
  setup() {
    const items = ref([]); const detailVisible = ref(false); const detail = ref({}); const page=ref(1),total=ref(0);
    const load = async () => { try { const r = await api.listNotifications({page:page.value,page_size:20}); items.value=r.items||[];total.value=r.meta.total; } catch(e) { ElMessage.error(e.message); } };
    const refresh=async()=>{await load();await loadUnread();};
    const follow=()=>{const d=detail.value.extra_data||{};let target='course/'+encodeURIComponent(d.course_id);if(d.topic_id)target+='?topic='+encodeURIComponent(d.topic_id);else if(d.peer_id)target+='?peer='+encodeURIComponent(d.peer_id);detailVisible.value=false;navigate(target);};
    const markAllRead = async () => { try { await api.markAllRead(); ElMessage.success("已全部标记为已读"); load(); loadUnread(); } catch(e) { ElMessage.error(e.message); } };
    const showDetail = (n) => { detail.value = n; detailVisible.value = true; if(!n.is_read) { api.markRead([n.id]).then(()=>{ load(); loadUnread(); }).catch(()=>{}); } };
    onMounted(load);
    return { page,total,load,refresh,follow,items, detailVisible, detail, markAllRead, showDetail };
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
      {key:'settings',label:'基础设置',icon:'Setting',role:'admin'},
      {key:'users',label:'用户与教师审核',icon:'UserFilled',perm:'user:read'},
      {key:'notifications',label:'消息中心',icon:'Bell'},
      {key:'profile',label:'个人中心',icon:'User'},
    ];
    const menuItems=computed(()=>{userInfo.value;return ALL_MENU_ITEMS.filter(m=>(!m.perm||api.hasPerm(m.perm))&&(!m.role||api.hasRole(m.role)));});
    const parseRoute = () => { const hash = window.location.hash.replace("#","")||"dashboard"; const parts = hash.split('?')[0].split("/"); currentPage.value=parts[0]; currentParam.value=parts[1]||null; if(api.isLoggedIn()) loadUnread(); };
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
    const componentMap={login:LoginPage,dashboard:DashboardPage,'my-courses':MyCoursesPage,courses:CourseListPage,course:CourseDetailPage,media:MediaPage,'question-banks':QuestionBankPage,exam:ExamTakePage,categories:CategoryPage,notifications:NotificationPage,users:UserManagePage,profile:ProfilePage,settings:PlatformSettingsPage};
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
        <div class="sidebar-logo">{{platform.platform_name}}</div>
        <el-scrollbar style="height:calc(100vh - 60px)">
          <el-menu :default-active="currentPage" background-color="#1e0f3f" text-color="#ffffffa6" active-text-color="#fff" @select="handleMenuSelect">
            <el-menu-item v-for="m in menuItems" :key="m.key" :index="m.key"><el-icon><component :is="m.icon" /></el-icon><span>{{ m.label }}</span><el-badge v-if="m.key==='notifications'&&unreadCount>0" class="badge-side" :value="unreadCount" position="top-right" style="margin-left:8px" /></el-menu-item>
          </el-menu>
        </el-scrollbar>
      </div>
    </el-drawer>
    <el-aside v-if="!isMobile" :width="sidebarCollapsed?'64px':'200px'">
      <div class="sidebar-logo" :title="platform.platform_name" style="overflow:hidden;white-space:nowrap;text-overflow:ellipsis">{{ sidebarCollapsed?'学':platform.platform_name }}</div>
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
  app.config.globalProperties.platform = platformState;
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
  api.getPlatformSettings().then(value=>{Object.assign(platformState,value);document.title=value.platform_name;}).catch(e=>ElMessage.error('平台设置读取失败：'+e.message));
} catch(e) {
  document.getElementById("app").innerHTML = '<div style="padding:40px;color:red;font-family:monospace">App Error: ' + e.message + "</div>";
}
