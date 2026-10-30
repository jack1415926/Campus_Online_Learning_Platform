// Runs the actual exam panel with shipped Vue; API responses are test doubles.
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {test} = require('node:test');
const root = resolve(__dirname, '../backend/static');

test('teacher can grade only nonempty pending answers in a mixed paper', async () => {
  const context = vm.createContext({console, ElementPlus:{ElMessage:{error(){}, warning(){}, success(){}}}});
  vm.runInContext(readFileSync(resolve(root, 'vendor/vue-3.5.13/vue.global.prod.js'), 'utf8'), context);
  vm.runInContext('Vue.onMounted=()=>{}; Vue.watch=()=>{};', context);
  vm.runInContext(readFileSync(resolve(root, 'js/exams.js'), 'utf8'), context);
  vm.runInContext(`
    var sent;
    var record={id:'record',status:'submitted',questions:[
      {id:'blank',type:'short_answer',content:'空白题',score:2},
      {id:'pending',type:'short_answer',content:'作答题',score:2}
    ],answers:[
      {question_id:'blank',answer:' ',score:0,graded:true},
      {question_id:'pending',answer:'文字',score:0,graded:false}
    ]};
    var api={getExamRecord:async()=>record,gradeExam:async(id,body)=>{sent=body},examRecords:async()=>({items:[],meta:{total:0}})};
    var page=CampusExamPanel.setup({course:{can_manage:true}});
  `, context);
  // loadRecords needs the selected exam set via the public UI action.
  await vm.runInContext("page.openRecords({id:'exam'});", context);
  await vm.runInContext("page.viewRecord({id:'record'});", context);
  const template = vm.runInContext('CampusExamPanel.template', context);
  vm.runInContext('Vue.compile(CampusExamPanel.template,{decodeEntities:text=>text})', context);
  const condition = template.match(/<div v-if="([^"]*canGrade\(q\)[^"]*)"/)[1];
  context.condition = condition;
  assert.equal(vm.runInContext("(()=>{const course={can_manage:true},detail=record,q=record.questions[0],canGrade=page.canGrade;return eval(condition)})()", context), false);
  assert.equal(vm.runInContext("(()=>{const course={can_manage:true},detail=record,q=record.questions[1],canGrade=page.canGrade;return eval(condition)})()", context), true);
  vm.runInContext("page.detail.value.answers[1].graded=true", context);
  assert.equal(vm.runInContext('page.canGrade(record.questions[1])', context), true);
  vm.runInContext("page.detail.value.answers[1].graded=false", context);
  vm.runInContext("page.grading.pending.score=2", context);
  await vm.runInContext('page.saveGrade()', context);
  assert.deepEqual(JSON.parse(vm.runInContext('JSON.stringify(sent.answers)', context)), [{question_id:'pending',score:2,grader_comment:''}]);
});
