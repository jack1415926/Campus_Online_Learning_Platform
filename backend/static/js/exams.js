// One course exam panel for manual papers, results and teacher grading.
const CampusExamPanel = {
  props:['course'],
  template:`<el-card shadow="never" style="margin-top:20px" v-if="course.can_manage||course.can_learn">
    <template #header><div style="display:flex;justify-content:space-between"><strong>课程考试</strong><div><el-button v-if="course.can_edit" @click="editExam()">添加考试</el-button><el-button @click="load">刷新</el-button></div></div></template>
    <el-empty v-if="!exams.length" description="暂无考试"/>
    <div v-for="e in exams" :key="e.id" style="padding:12px 0;border-bottom:1px solid #eee">
      <strong>{{e.title}}</strong><p>{{e.description}}</p><p>开放：{{fmtDateTime(e.start_time)}} ～ {{fmtDateTime(e.end_time)}} · {{e.duration_minutes}}分钟 · 及格{{e.pass_score}}% · 最多{{e.max_attempts}}次</p>
      <p v-if="e.grading_notes" style="white-space:pre-wrap">评分说明：{{e.grading_notes}}</p>
      <el-button v-if="course.can_edit" @click="editExam(e)">编辑考试</el-button><el-button v-if="course.can_edit" type="danger" plain @click="remove(e)">删除考试</el-button>
      <el-button v-if="!course.can_manage&&course.status==='published'" type="primary" @click="navigate('exam/'+e.id)">开始或继续考试</el-button>
      <el-button :aria-label="(course.can_manage?'答卷与阅卷：':'我的成绩：')+e.title" @click="openRecords(e)">{{course.can_manage?'答卷与阅卷':'我的成绩'}}</el-button>
    </div>
    <el-pagination v-if="total>20" v-model:current-page="page" :total="total" :page-size="20" @current-change="load" layout="prev,pager,next"/>
    <el-dialog v-model="showEdit" :title="editing?'编辑考试':'添加考试'" width="800px">
      <el-form label-position="top"><el-form-item label="考试标题"><el-input v-model="form.title"/></el-form-item><el-form-item label="考试说明"><el-input type="textarea" v-model="form.description"/></el-form-item>
        <el-form-item label="开放起止时间（北京时间）"><el-date-picker v-model="form.start_time" type="datetime"/><span> ～ </span><el-date-picker v-model="form.end_time" type="datetime"/></el-form-item>
        <el-form-item label="答题时长（分钟）"><el-input-number v-model="form.duration_minutes" :min="1" :max="300"/></el-form-item>
        <el-form-item label="及格百分比"><el-input-number v-model="form.pass_score" :min="0" :max="100"/></el-form-item><el-form-item label="最多尝试次数"><el-input-number v-model="form.max_attempts" :min="1" :max="10"/></el-form-item>
        <el-form-item label="评分说明"><el-input v-model="form.grading_notes" type="textarea"/></el-form-item>
      </el-form>
      <p>从本人题库手动选题，已选 {{selectedIds.length}} 题；可调整每题分值。题目在保存试卷时固定。</p>
      <el-select v-model="bankId" placeholder="全部本人题目" clearable @change="questionPage=1;loadQuestions()"><el-option v-for="b in banks" :key="b.id" :label="b.name" :value="b.id"/></el-select>
      <el-checkbox-group v-model="selectedIds"><div v-for="q in questions" :key="q.id" style="padding:8px 0"><el-checkbox :value="q.id">{{q.content}}（{{types[q.question_type]}}）</el-checkbox><el-input-number v-if="selectedIds.includes(q.id)" v-model="scores[q.id]" :min="0.5" :max="10000" :step="0.5" size="small"/></div></el-checkbox-group>
      <el-pagination v-if="questionTotal>20" v-model:current-page="questionPage" :total="questionTotal" :page-size="20" @current-change="loadQuestions" layout="prev,pager,next"/>
      <template #footer><el-button @click="showEdit=false">取消</el-button><el-button type="primary" :loading="busy" @click="saveExam">保存考试</el-button></template>
    </el-dialog>
    <el-dialog v-model="showRecords" :title="course.can_manage?'答卷与阅卷':'我的成绩'" width="900px">
      <el-empty v-if="!records.length" :description="course.can_manage?'暂无答卷':'尚未参加本场考试'"/>
      <el-table :data="records" stripe><el-table-column label="学生"><template #default="{row}">{{row.full_name||'本人'}}</template></el-table-column><el-table-column prop="attempt_number" label="次数"/>
        <el-table-column label="状态"><template #default="{row}">{{statuses[row.status]}}</template></el-table-column><el-table-column label="得分"><template #default="{row}">{{row.total_score}} / {{row.max_score}}</template></el-table-column>
        <el-table-column label="最终结果"><template #default="{row}">{{row.is_pass===null?'尚无最终结论':row.is_pass?'通过':'未通过'}}</template></el-table-column><el-table-column label="操作"><template #default="{row}"><el-button @click="viewRecord(row)">{{course.can_manage?'查看/阅卷':'查看结果'}}</el-button></template></el-table-column></el-table>
      <el-pagination v-if="recordTotal>20" v-model:current-page="recordPage" :total="recordTotal" :page-size="20" @current-change="loadRecords" layout="prev,pager,next"/>
    </el-dialog>
    <el-dialog v-model="showDetail" title="答卷详情" width="850px">
      <template v-if="detail"><p>{{statuses[detail.status]}} · {{detail.total_score}} / {{detail.max_score}} · {{detail.is_pass===null?'尚无最终结论':detail.is_pass?'通过':'未通过'}}</p>
        <div v-for="q in detail.questions" :key="q.id" style="padding:12px 0;border-bottom:1px solid #eee"><strong>{{q.content}}</strong>（{{types[q.type]}}，{{q.score}}分）
          <p v-for="o in q.options||[]" :key="o.key">{{o.key}}. {{o.text}}</p>
          <p style="white-space:pre-wrap">学生答案：{{format(answerFor(q.id)?.answer)}}</p><p v-if="q.correct_answer!==undefined" style="white-space:pre-wrap">{{q.type==='short_answer'?'参考答案':'正确答案'}}：{{format(q.correct_answer)}}</p>
          <p v-if="answerFor(q.id)?.graded">得分：{{answerFor(q.id).score}}　评语：{{answerFor(q.id).grader_comment||'无'}}</p><p v-else>待批改</p>
          <div v-if="course.can_manage&&canGrade(q)&&detail.status==='submitted'"><el-input-number v-model="grading[q.id].score" :min="0" :max="q.score" :aria-label="'给简答题评分：'+q.content"/><el-input v-model="grading[q.id].grader_comment" type="textarea" placeholder="教师评语"/></div>
        </div>
        <p v-if="detail.status==='graded'">最终成绩已发布，不再重新评分。</p>
        <el-button v-if="course.can_manage&&detail.status==='submitted'&&detail.questions.some(canGrade)" type="primary" :loading="busy" @click="saveGrade">保存批改</el-button>
      </template>
    </el-dialog>
  </el-card>`,
  setup(props){
    const {ref,reactive,onMounted,watch}=Vue;
    const exams=ref([]),total=ref(0),page=ref(1),showEdit=ref(false),editing=ref(null),busy=ref(false),banks=ref([]),bankId=ref(''),questions=ref([]),questionPage=ref(1),questionTotal=ref(0),selectedIds=ref([]),scores=reactive({});
    const form=reactive({title:'',description:'',start_time:null,end_time:null,duration_minutes:60,pass_score:60,max_attempts:1,grading_notes:''});
    const showRecords=ref(false),selectedExam=ref(null),records=ref([]),recordPage=ref(1),recordTotal=ref(0),showDetail=ref(false),detail=ref(null),grading=reactive({});
    const types={single_choice:'单选',multiple_choice:'多选',true_false:'判断',short_answer:'简答'},statuses={in_progress:'进行中',submitted:'待批改',graded:'已批改',not_started:'未开始'};
    const error=e=>ElementPlus.ElMessage.error(e.message);
    const load=async()=>{if(!props.course.can_manage&&!props.course.can_learn)return;try{const r=await api.listExams({course_id:props.course.id,page:page.value,page_size:20});exams.value=r.items;total.value=r.meta.total;}catch(e){error(e);}};
    const loadQuestions=async()=>{try{const r=await api.listQuestions({page:questionPage.value,page_size:20,...(bankId.value?{question_bank_id:bankId.value}:{})});questions.value=r.items;questionTotal.value=r.meta.total;for(const q of r.items)if(scores[q.id]===undefined)scores[q.id]=q.score;}catch(e){error(e);}};
    const editExam=async e=>{editing.value=e?.id||null;selectedIds.value=[...(e?.question_ids||[])];for(const k of Object.keys(scores))delete scores[k];Object.assign(scores,e?.question_scores||{});Object.assign(form,e?{title:e.title,description:e.description||'',start_time:new Date(e.start_time),end_time:new Date(e.end_time),duration_minutes:e.duration_minutes,pass_score:e.pass_score,max_attempts:e.max_attempts,grading_notes:e.grading_notes||''}:{title:'',description:'',start_time:new Date(),end_time:new Date(Date.now()+86400000),duration_minutes:60,pass_score:60,max_attempts:1,grading_notes:''});questionPage.value=1;bankId.value='';try{banks.value=await api.listQuestionBanks();await loadQuestions();showEdit.value=true;}catch(e){error(e);}};
    const saveExam=async()=>{if(!form.title.trim()||!form.start_time||!form.end_time||!selectedIds.value.length)return ElementPlus.ElMessage.warning('请填写标题、起止时间并选择题目');busy.value=true;try{await api.saveExam(editing.value,{...form,course_id:props.course.id,start_time:new Date(form.start_time).toISOString(),end_time:new Date(form.end_time).toISOString(),question_ids:selectedIds.value,question_scores:Object.fromEntries(selectedIds.value.map(id=>[id,scores[id]]))});showEdit.value=false;await load();ElementPlus.ElMessage.success('考试已保存');}catch(e){error(e);}finally{busy.value=false;}};
    const remove=async e=>{try{await ElementPlus.ElMessageBox.confirm('确认删除草稿考试？','删除确认');await api.deleteExam(e.id);await load();}catch(e){if(e?.message)error(e);}};
    const loadRecords=async()=>{try{if(props.course.can_manage){const r=await api.examRecords(selectedExam.value.id,recordPage.value);records.value=r.items;recordTotal.value=r.meta.total;}else{const r=await api.getMyExamRecords(selectedExam.value.id);recordTotal.value=r.length;records.value=r.slice((recordPage.value-1)*20,recordPage.value*20);}}catch(e){error(e);}};
    const openRecords=async e=>{selectedExam.value=e;recordPage.value=1;await loadRecords();showRecords.value=true;};
    const answerFor=id=>detail.value?.answers?.find(a=>a.question_id===id);
    const canGrade=q=>q.type==='short_answer'&&typeof answerFor(q.id)?.answer==='string'&&!!answerFor(q.id).answer.trim();
    const viewRecord=async row=>{try{detail.value=await api.getExamRecord(row.id);for(const q of detail.value.questions){const a=answerFor(q.id);grading[q.id]={score:a?.graded?a.score:null,grader_comment:a?.grader_comment||''};}showDetail.value=true;}catch(e){error(e);}};
    const saveGrade=async()=>{const answers=detail.value.questions.filter(q=>canGrade(q)&&grading[q.id].score!==null&&grading[q.id].score!==undefined).map(q=>({question_id:q.id,...grading[q.id]}));if(!answers.length)return ElementPlus.ElMessage.warning('请为至少一道简答题填写分数，允许0分');busy.value=true;try{await api.gradeExam(detail.value.id,{answers});await viewRecord({id:detail.value.id});await loadRecords();ElementPlus.ElMessage.success('批改已保存');}catch(e){error(e);}finally{busy.value=false;}};
    const format=value=>Array.isArray(value)?value.join('、'):value??'未作答';
    onMounted(load);watch(()=>props.course.can_learn,load);
    return{exams,total,page,showEdit,editing,busy,banks,bankId,questions,questionPage,questionTotal,selectedIds,scores,form,showRecords,records,recordPage,recordTotal,showDetail,detail,grading,types,statuses,load,loadQuestions,editExam,saveExam,remove,openRecords,loadRecords,viewRecord,answerFor,canGrade,saveGrade,format};
  }
};
