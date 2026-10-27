// Course-local homework and a plain teacher roster; no separate detail routes.
const HomeworkPanel = {
  props: ['course'],
  template: `<el-card shadow="never" style="margin-top:20px" v-if="course.can_manage || course.can_learn">
    <template #header><div style="display:flex;justify-content:space-between"><strong>课程作业</strong><div>
      <el-button v-if="course.can_edit" @click="editHomework()">添加作业</el-button>
      <el-button v-if="course.can_manage" @click="openStudents">学生进度</el-button><el-button @click="load">刷新</el-button>
    </div></div></template>
    <el-alert v-if="course.status==='archived'" title="课程已归档，保留历史作业与批改结果，不接受新提交。" type="info" :closable="false"/>
    <el-empty v-if="!items.length" description="暂无作业"/>
    <div v-for="h in items" :key="h.id" style="padding:16px 0;border-bottom:1px solid #eee">
      <strong>{{h.title}}</strong><span style="margin-left:12px">{{h.max_score}} 分 · {{h.is_required?'必交':'选交'}} · 截止 {{fmtDateTime(h.due_at)}}</span>
      <p style="white-space:pre-wrap">{{h.description}}</p><p v-if="h.grading_notes" style="white-space:pre-wrap">评分说明：{{h.grading_notes}}</p>
      <template v-if="course.can_manage"><el-button v-if="course.can_edit" @click="editHomework(h)">编辑</el-button><el-button v-if="course.can_edit" type="danger" plain @click="remove(h)">删除</el-button><el-button @click="openSubmissions(h)">查看提交与批改</el-button></template>
      <template v-else>
        <el-tag>{{!h.submission?'未提交':h.submission.graded_at?'已批改':'待批改'}}</el-tag>
        <div v-if="h.submission"><p style="white-space:pre-wrap">我的提交：{{h.submission.text}}</p>
          <el-button v-if="h.submission.attachment_name" text @click="download(h,h.submission)">{{h.submission.attachment_name}}</el-button>
          <p v-if="h.submission.graded_at" style="white-space:pre-wrap">得分：{{h.submission.score}} / {{h.max_score}}　评语：{{h.submission.feedback||'无'}}</p></div>
        <el-button v-if="course.status==='published' && !h.submission?.graded_at && Date.now()<Date.parse(h.due_at)" type="primary" @click="openSubmit(h)">{{h.submission?'修改提交':'提交作业'}}</el-button>
        <span v-else-if="!h.submission?.graded_at">已截止或课程已归档</span>
      </template>
    </div>
    <el-pagination v-if="total>20" v-model:current-page="page" :page-size="20" :total="total" @current-change="load" layout="prev,pager,next"/>
    <el-dialog v-model="showEdit" :title="editing?'编辑作业':'添加作业'" width="600px">
      <el-form label-position="top"><el-form-item label="作业标题"><el-input v-model="form.title"/></el-form-item>
        <el-form-item label="作业要求"><el-input v-model="form.description" type="textarea" :rows="4"/></el-form-item>
        <el-form-item label="截止时间（北京时间）"><el-date-picker v-model="form.due_at" type="datetime"/></el-form-item>
        <el-form-item label="满分"><el-input-number v-model="form.max_score" :min="1" :max="10000"/></el-form-item>
        <el-form-item label="评分说明"><el-input v-model="form.grading_notes" type="textarea"/></el-form-item>
        <el-form-item label="必交"><el-switch v-model="form.is_required"/></el-form-item></el-form>
      <template #footer><el-button @click="showEdit=false">取消</el-button><el-button type="primary" :loading="busy" @click="save">保存作业</el-button></template>
    </el-dialog>
    <el-dialog v-model="showSubmit" title="提交作业" width="600px" destroy-on-close>
      <p>{{selected?.title}}（截止 {{fmtDateTime(selected?.due_at)}}）</p>
      <el-form label-position="top"><el-form-item label="作业文字"><el-input v-model="submissionText" type="textarea" :rows="5" maxlength="20000"/></el-form-item>
        <el-form-item label="单个附件（PDF/DOCX/JPG/PNG，最多20MB）"><input type="file" accept=".pdf,.docx,.jpg,.jpeg,.png" @change="selectFile"/></el-form-item>
        <el-checkbox v-if="selected?.submission?.attachment_name" v-model="removeAttachment">删除原附件：{{selected.submission.attachment_name}}</el-checkbox></el-form>
      <template #footer><el-button @click="showSubmit=false">取消</el-button><el-button type="primary" :loading="busy" @click="submit">保存提交</el-button></template>
    </el-dialog>
    <el-dialog v-model="showGrades" title="提交与批改" width="90%">
      <p>{{selected?.title}} · 满分 {{selected?.max_score}} · 空分数表示待批改，0分表示已批改。</p>
      <el-table :data="submissions" stripe><el-table-column prop="full_name" label="学生" width="120"/>
        <el-table-column label="提交内容" min-width="220"><template #default="{row}"><div style="white-space:pre-wrap">{{row.text}}</div><el-button v-if="row.attachment_name" text @click="download(selected,row)">{{row.attachment_name}}</el-button></template></el-table-column>
        <el-table-column label="状态" width="90"><template #default="{row}">{{row.graded_at?'已批改':'待批改'}}</template></el-table-column>
        <el-table-column label="分数" width="170"><template #default="{row}"><el-input-number v-model="row.score" :min="0" :max="selected.max_score"/></template></el-table-column>
        <el-table-column label="评语" min-width="160"><template #default="{row}"><el-input v-model="row.feedback" type="textarea"/></template></el-table-column>
        <el-table-column label="操作" width="100"><template #default="{row}"><el-button :loading="busy" @click="grade(row)">保存批改</el-button></template></el-table-column></el-table>
      <el-pagination v-if="submissionTotal>20" v-model:current-page="submissionPage" :page-size="20" :total="submissionTotal" @current-change="loadSubmissions" layout="prev,pager,next"/>
    </el-dialog>
    <el-dialog v-model="showStudents" title="学生进度与作业状态" width="800px">
      <el-table :data="students" stripe><el-table-column prop="full_name" label="学生"/>
        <el-table-column label="章节进度"><template #default="{row}">{{row.completed_chapters}} / {{row.total_chapters}}（{{row.overall_percent}}%）</template></el-table-column>
        <el-table-column label="已提交作业"><template #default="{row}">{{row.submitted}} / {{row.homework_total}}</template></el-table-column><el-table-column prop="graded" label="已批改作业"/>
        <el-table-column label="最终考试成绩"><template #default="{row}"><div v-for="r in row.exam_results" :key="r.exam_id+'-'+r.attempt_number">{{r.title}}（第{{r.attempt_number}}次）：{{r.total_score}} / {{r.max_score}}，{{r.is_pass?'通过':'未通过'}}</div><span v-if="!row.exam_results?.length">暂无最终成绩</span></template></el-table-column></el-table>
      <el-pagination v-if="studentTotal>20" v-model:current-page="studentPage" :page-size="20" :total="studentTotal" @current-change="loadStudents" layout="prev,pager,next"/>
    </el-dialog>
  </el-card>`,
  setup(props) {
    const {ref,reactive,onMounted,watch}=Vue;
    const items=ref([]),total=ref(0),page=ref(1),busy=ref(false),editing=ref(null),selected=ref(null);
    const showEdit=ref(false),showSubmit=ref(false),showGrades=ref(false),showStudents=ref(false);
    const form=reactive({title:'',description:'',due_at:null,max_score:100,grading_notes:'',is_required:true});
    const submissionText=ref(''),removeAttachment=ref(false),submissions=ref([]),submissionTotal=ref(0),submissionPage=ref(1),students=ref([]),studentTotal=ref(0),studentPage=ref(1);let file=null;
    const load=async()=>{if(!props.course.can_manage&&!props.course.can_learn)return;try{const r=await api.listHomeworks(props.course.id,page.value);items.value=r.items;total.value=r.meta.total;}catch(e){ElementPlus.ElMessage.error(e.message);}};
    const editHomework=h=>{editing.value=h?.id||null;Object.assign(form,h?{title:h.title,description:h.description,due_at:new Date(h.due_at),max_score:h.max_score,grading_notes:h.grading_notes,is_required:h.is_required}:{title:'',description:'',due_at:new Date(Date.now()+86400000),max_score:100,grading_notes:'',is_required:true});showEdit.value=true;};
    const save=async()=>{if(!form.title.trim()||!form.description.trim()||!form.due_at)return ElementPlus.ElMessage.warning('请填写标题、要求及截止时间');busy.value=true;try{await api.saveHomework(props.course.id,editing.value,{...form,due_at:new Date(form.due_at).toISOString()});showEdit.value=false;await load();ElementPlus.ElMessage.success('作业已保存');}catch(e){ElementPlus.ElMessage.error(e.message);}finally{busy.value=false;}};
    const remove=async h=>{try{await ElementPlus.ElMessageBox.confirm('确认删除草稿作业？','删除确认');await api.deleteHomework(props.course.id,h.id);await load();}catch(e){if(e?.message)ElementPlus.ElMessage.error(e.message);}};
    const openSubmit=h=>{selected.value=h;submissionText.value=h.submission?.text||'';removeAttachment.value=false;file=null;showSubmit.value=true;};
    const selectFile=e=>{file=e.target.files[0]||null;if(file&&file.size>20*1024*1024){file=null;e.target.value='';ElementPlus.ElMessage.error('附件不能超过20MB');}};
    const submit=async()=>{busy.value=true;try{const body=new FormData();body.append('text',submissionText.value);body.append('remove_attachment',removeAttachment.value);if(file)body.append('file',file);await api.submitHomework(props.course.id,selected.value.id,body);showSubmit.value=false;await load();ElementPlus.ElMessage.success('提交已保存');}catch(e){ElementPlus.ElMessage.error(e.message);}finally{busy.value=false;}};
    const loadSubmissions=async()=>{try{const r=await api.homeworkSubmissions(props.course.id,selected.value.id,submissionPage.value);submissions.value=r.items;submissionTotal.value=r.meta.total;}catch(e){ElementPlus.ElMessage.error(e.message);}};
    const openSubmissions=async h=>{selected.value=h;submissionPage.value=1;await loadSubmissions();showGrades.value=true;};
    const grade=async row=>{if(row.score===null||row.score===undefined)return ElementPlus.ElMessage.warning('请填写分数，允许0分');busy.value=true;try{await api.gradeHomework(props.course.id,selected.value.id,row.id,{score:row.score,feedback:row.feedback||''});await loadSubmissions();ElementPlus.ElMessage.success('批改已保存');}catch(e){ElementPlus.ElMessage.error(e.message);}finally{busy.value=false;}};
    const download=async(h,s)=>{try{await api.downloadHomework(props.course.id,h.id,s);}catch(e){ElementPlus.ElMessage.error(e.message);}};
    const loadStudents=async()=>{try{const r=await api.courseStudents(props.course.id,studentPage.value);students.value=r.items;studentTotal.value=r.meta.total;}catch(e){ElementPlus.ElMessage.error(e.message);}};
    const openStudents=async()=>{studentPage.value=1;await loadStudents();showStudents.value=true;};
    onMounted(load);watch(()=>props.course.can_learn,load);
    return{items,total,page,busy,editing,selected,showEdit,showSubmit,showGrades,showStudents,form,submissionText,removeAttachment,submissions,submissionTotal,submissionPage,students,studentTotal,studentPage,load,editHomework,save,remove,openSubmit,selectFile,submit,loadSubmissions,openSubmissions,grade,download,loadStudents,openStudents};
  }
};
