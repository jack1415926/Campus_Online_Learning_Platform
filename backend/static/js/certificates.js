// A fixed course certificate; the browser handles printing and Save as PDF.
const CertificatePanel = {
  props:['course'],
  template:`<el-card v-if="course.can_manage||course.can_learn" shadow="never" style="margin-top:20px">
    <template #header><div style="display:flex;justify-content:space-between"><strong>课程证书</strong><el-button @click="load">刷新证书</el-button></div></template>
    <template v-if="course.can_manage">
      <el-form v-if="course.can_edit" label-position="top"><el-form-item label="结课考核（不选择表示不启用证书）">
        <el-select v-model="examId" clearable placeholder="选择本课程考试" style="width:100%" @visible-change="v=>v&&loadExams()"><el-option v-for="e in exams" :key="e.id" :label="e.title" :value="e.id"/></el-select>
      </el-form-item><el-button type="primary" :loading="busy" @click="save">保存证书设置</el-button></el-form>
      <p v-else>证书规则已冻结：{{examTitle}}。</p>
      <p style="margin:12px 0">领取条件：完成全部章节、所有必交作业已提交且已批改、指定考试最终及格。</p>
      <el-table :data="items" stripe><el-table-column prop="student_name" label="学生"/><el-table-column prop="number" label="证书编号" min-width="260"/><el-table-column label="颁发日期"><template #default="{row}">{{date(row.issued_at)}}</template></el-table-column></el-table>
      <el-empty v-if="!items.length" description="尚未颁发证书"/><el-pagination v-if="total>20" v-model:current-page="page" :total="total" :page-size="20" @current-change="load" layout="prev,pager,next"/>
    </template>
    <template v-else-if="state">
      <template v-if="state.certificate"><p>已领取证书：{{state.certificate.number}}</p><el-button type="primary" @click="show=true">查看与打印证书</el-button></template>
      <template v-else><p v-for="reason in state.reasons" :key="reason">{{reason}}</p><p v-if="state.eligible">已满足领取条件。</p><p v-if="course.status==='archived'">课程已归档，不再新发证书。</p><el-button v-if="state.enabled" type="primary" :disabled="!state.eligible||course.status!=='published'" :loading="busy" @click="claim">领取证书</el-button></template>
    </template>
    <el-dialog v-model="show" title="结课证书" width="850px" append-to-body>
      <div v-if="state?.certificate" class="certificate-sheet" style="border:6px double #7c3aed;padding:45px;text-align:center;background:white;color:#303133">
        <h1 style="font-size:32px;margin:16px">结课证书</h1><p style="margin:20px">{{state.certificate.student_name}} 同学：</p>
        <p style="line-height:2.5;white-space:pre-wrap">你已完成《{{state.certificate.course_title}}》课程学习及规定考核，特颁发此证。</p>
        <p style="margin:24px">{{state.certificate.platform_name}}</p><p>颁发日期：{{date(state.certificate.issued_at)}}</p><p style="font-size:12px;margin-top:24px;overflow-wrap:anywhere">证书编号：{{state.certificate.number}}</p>
      </div><template #footer><el-button @click="show=false">关闭</el-button><el-button type="primary" @click="print">打印 / 另存 PDF</el-button></template>
    </el-dialog>
  </el-card>`,
  setup(props){
    const {ref,computed,onMounted,watch}=Vue;
    const exams=ref([]),examId=ref(null),savedId=ref(null),items=ref([]),page=ref(1),total=ref(0),state=ref(null),busy=ref(false),show=ref(false);
    const error=e=>ElementPlus.ElMessage.error(e.message);
    const examTitle=computed(()=>!savedId.value?'未启用':exams.value.find(e=>e.id===savedId.value)?.title||'已指定结课考试');
    const loadExams=async()=>{const r=await api.listExams({course_id:props.course.id,page_size:500});exams.value=r.items;};
    const load=async()=>{if(!props.course.can_manage&&!props.course.can_learn)return;try{if(props.course.can_manage){const c=await api.getCourse(props.course.id);savedId.value=examId.value=c.certificate_exam_id;await loadExams();const r=await api.courseCertificates(props.course.id,page.value);items.value=r.items;total.value=r.meta.total;}else state.value=await api.certificateStatus(props.course.id);}catch(e){error(e);}};
    const save=async()=>{busy.value=true;try{await api.updateCourse(props.course.id,{certificate_exam_id:examId.value||null});await load();ElementPlus.ElMessage.success('证书设置已保存');}catch(e){error(e);}finally{busy.value=false;}};
    const claim=async()=>{busy.value=true;try{await api.claimCertificate(props.course.id);await load();show.value=!!state.value?.certificate;}catch(e){error(e);}finally{busy.value=false;}};
    const date=value=>new Date(value+'Z').toLocaleDateString('zh-CN',{timeZone:'Asia/Shanghai'});
    const print=()=>window.print();
    onMounted(load);watch(()=>props.course.can_learn,load);
    return{exams,examId,items,page,total,state,busy,show,examTitle,loadExams:()=>loadExams().catch(error),load,save,claim,date,print};
  }
};
