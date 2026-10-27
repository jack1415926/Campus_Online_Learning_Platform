// Minimal course discussion and teacher/student messages, refreshed on demand.
const CommunicationPanel = {
  props:['course'],
  template:`<el-card shadow="never" style="margin-top:20px" v-if="course.can_manage||course.can_learn">
    <el-tabs v-model="tab" @tab-change="changeTab"><el-tab-pane label="课程讨论" name="discussion">
      <div style="display:flex;gap:8px;margin-bottom:12px"><el-button v-if="canPost" type="primary" @click="showCreate=true">发布主题</el-button><el-button @click="loadTopics">刷新讨论</el-button></div>
      <el-alert v-if="course.status==='archived'" title="课程已归档，只能查看历史内容和按权限删除讨论。" :closable="false" type="info"/>
      <el-table :data="topics" stripe><el-table-column prop="title" label="主题"/><el-table-column prop="full_name" label="作者" width="140"/>
        <el-table-column label="时间" width="180"><template #default="{row}">{{fmtDateTime(row.created_at)}}</template></el-table-column>
        <el-table-column label="操作" width="180"><template #default="{row}"><el-button :aria-label="'查看主题：'+row.title" @click="openTopic(row.id)">查看</el-button><el-button v-if="row.can_delete" text type="danger" @click="deleteTopic(row)">删除</el-button></template></el-table-column></el-table>
      <el-empty v-if="!topics.length" description="暂无讨论"/>
      <el-pagination v-if="topicTotal>20" v-model:current-page="topicPage" :total="topicTotal" :page-size="20" @current-change="loadTopics" layout="prev,pager,next"/>
    </el-tab-pane><el-tab-pane v-if="canPrivate" label="师生私信" name="private">
      <el-button @click="loadContacts">刷新联系人</el-button><p>学生只能联系本课程任课教师；教师只能联系本人课程的学生。</p>
      <el-table :data="contacts" stripe><el-table-column prop="full_name" label="课程联系人"/><el-table-column prop="unread" label="未读私信"/><el-table-column label="操作"><template #default="{row}"><el-button :aria-label="'打开会话：'+row.full_name" @click="openConversation(row.id)">打开会话</el-button></template></el-table-column></el-table>
      <el-empty v-if="!contacts.length" description="暂无课程联系人"/><el-pagination v-if="contactTotal>20" v-model:current-page="contactPage" :total="contactTotal" :page-size="20" @current-change="loadContacts" layout="prev,pager,next"/>
    </el-tab-pane></el-tabs>
    <el-dialog v-model="showCreate" title="发布讨论主题" width="600px"><el-form label-position="top"><el-form-item label="主题标题"><el-input v-model="topicForm.title" maxlength="255"/></el-form-item><el-form-item label="主题内容"><el-input v-model="topicForm.body" type="textarea" :rows="5" maxlength="20000"/></el-form-item></el-form><template #footer><el-button @click="showCreate=false">取消</el-button><el-button :loading="busy" type="primary" @click="createTopic">发布</el-button></template></el-dialog>
    <el-dialog v-model="showTopic" title="讨论详情" width="800px">
      <template v-if="topic"><h3>{{topic.title}}</h3><p>{{topic.full_name}} · {{fmtDateTime(topic.created_at)}}</p><div style="white-space:pre-wrap">{{topic.body}}</div>
        <el-button @click="loadReplies">刷新回复</el-button><div v-for="r in replies" :key="r.id" style="padding:12px 0;border-bottom:1px solid #eee"><p>{{r.full_name}} · {{fmtDateTime(r.created_at)}} <el-button v-if="r.can_delete" text type="danger" @click="deleteReply(r)">删除回复</el-button></p><div style="white-space:pre-wrap">{{r.body}}</div></div>
        <el-pagination v-if="replyTotal>20" v-model:current-page="replyPage" :total="replyTotal" :page-size="20" @current-change="loadReplies" layout="prev,pager,next"/>
        <el-form v-if="canPost" label-position="top"><el-form-item label="回复内容"><el-input v-model="replyBody" type="textarea" :rows="3" maxlength="20000"/></el-form-item><el-button :loading="busy" type="primary" @click="reply">发表回复</el-button></el-form>
      </template>
    </el-dialog>
    <el-dialog v-if="canPrivate" v-model="showConversation" :title="'与'+(peer?.full_name||'课程联系人')+'的私信'" width="700px">
      <el-button @click="loadMessages">刷新会话</el-button><p v-if="messagePage===1">最新消息</p>
      <div v-for="m in messages" :key="m.id" style="padding:12px 0;border-bottom:1px solid #eee"><p>{{m.sender_id===api._user.id?'我':peer?.full_name}} · {{fmtDateTime(m.created_at)}} <el-tag v-if="m.sender_id===api._user.id" size="small">{{m.read_at?'已读':'未读'}}</el-tag></p><div style="white-space:pre-wrap">{{m.body}}</div></div>
      <el-empty v-if="!messages.length" description="暂无往来私信"/><el-pagination v-if="messageTotal>20" v-model:current-page="messagePage" :total="messageTotal" :page-size="20" @current-change="loadMessages" layout="prev,pager,next"/>
      <el-form v-if="course.status==='published'" label-position="top"><el-form-item label="私信内容"><el-input v-model="messageBody" type="textarea" :rows="3" maxlength="20000"/></el-form-item><el-button type="primary" :loading="busy" @click="sendMessage">发送私信</el-button></el-form><p v-else>课程已归档，不接受新私信。</p>
    </el-dialog>
  </el-card>`,
  setup(props){
    const {ref,reactive,computed,onMounted,onUnmounted,watch}=Vue;
    const tab=ref('discussion'),topics=ref([]),topicTotal=ref(0),topicPage=ref(1),showCreate=ref(false),busy=ref(false),topicForm=reactive({title:'',body:''}),topic=ref(null),showTopic=ref(false),replies=ref([]),replyTotal=ref(0),replyPage=ref(1),replyBody=ref('');
    const contacts=ref([]),contactTotal=ref(0),contactPage=ref(1),peer=ref(null),showConversation=ref(false),messages=ref([]),messageTotal=ref(0),messagePage=ref(1),messageBody=ref('');
    const canPrivate=computed(()=>!api.hasRole('admin')&&(api.hasRole('student')||api.hasRole('teacher')&&props.course.can_manage));
    const canPost=computed(()=>props.course.status==='published'&&(api.hasRole('student')&&props.course.can_learn||api.hasRole('teacher')&&props.course.can_manage));
    const error=e=>ElementPlus.ElMessage.error(e.message);
    const loadTopics=async()=>{try{const r=await api.listTopics(props.course.id,topicPage.value);topics.value=r.items;topicTotal.value=r.meta.total;}catch(e){error(e);}};
    const createTopic=async()=>{if(!topicForm.title.trim()||!topicForm.body.trim())return ElementPlus.ElMessage.warning('请填写标题和内容');busy.value=true;try{await api.createTopic(props.course.id,{...topicForm});showCreate.value=false;topicForm.title=topicForm.body='';topicPage.value=1;await loadTopics();}catch(e){error(e);}finally{busy.value=false;}};
    const loadReplies=async()=>{if(!topic.value)return;try{const r=await api.getTopic(props.course.id,topic.value.id,replyPage.value);topic.value=r.topic;replies.value=r.items;replyTotal.value=r.meta.total;await loadUnread();}catch(e){showTopic.value=false;error(e);}};
    const openTopic=async id=>{topic.value={id};replyPage.value=1;replyBody.value='';await loadReplies();if(topic.value?.title)showTopic.value=true;};
    const reply=async()=>{if(!replyBody.value.trim())return ElementPlus.ElMessage.warning('请输入回复');busy.value=true;try{await api.replyTopic(props.course.id,topic.value.id,{body:replyBody.value});replyBody.value='';replyPage.value=Math.floor(replyTotal.value/20)+1;await loadReplies();}catch(e){error(e);}finally{busy.value=false;}};
    const deleteTopic=async row=>{try{await ElementPlus.ElMessageBox.confirm('删除主题后其回复也不再显示，是否继续？','删除确认');await api.deleteTopic(props.course.id,row.id);topicPage.value=1;await loadTopics();}catch(e){if(e?.message)error(e);}};
    const deleteReply=async row=>{try{await ElementPlus.ElMessageBox.confirm('确认删除该回复？','删除确认');await api.deleteReply(props.course.id,topic.value.id,row.id);replyPage.value=1;await loadReplies();}catch(e){if(e?.message)error(e);}};
    const loadContacts=async()=>{if(!canPrivate.value)return;try{const r=await api.privateContacts(props.course.id,contactPage.value);contacts.value=r.items;contactTotal.value=r.meta.total;}catch(e){error(e);}};
    const loadMessages=async()=>{if(!peer.value)return;try{const r=await api.conversation(props.course.id,peer.value.id,messagePage.value);peer.value=r.peer;messages.value=r.items;messageTotal.value=r.meta.total;await loadContacts();await loadUnread();}catch(e){showConversation.value=false;error(e);}};
    const openConversation=async id=>{peer.value={id};messagePage.value=1;messageBody.value='';await loadMessages();if(peer.value?.full_name)showConversation.value=true;};
    const sendMessage=async()=>{if(!messageBody.value.trim())return ElementPlus.ElMessage.warning('请输入私信内容');busy.value=true;try{await api.sendMessage(props.course.id,{recipient_id:peer.value.id,body:messageBody.value});messageBody.value='';messagePage.value=1;await loadMessages();}catch(e){error(e);}finally{busy.value=false;}};
    const changeTab=async name=>{if(name==='private')await loadContacts();else await loadTopics();};
    const handleTarget=async()=>{const [path,query]=window.location.hash.slice(1).split('?');if(path!=='course/'+props.course.id)return;const target=new URLSearchParams(query||'');if(target.has('topic')){tab.value='discussion';await openTopic(target.get('topic'));}else if(target.has('peer')&&canPrivate.value){tab.value='private';await loadContacts();await openConversation(target.get('peer'));}};
    const initialize=async()=>{if(!props.course.can_manage&&!props.course.can_learn)return;await loadTopics();await handleTarget();};
    onMounted(()=>{initialize();window.addEventListener('hashchange',handleTarget);});onUnmounted(()=>window.removeEventListener('hashchange',handleTarget));watch(()=>props.course.can_learn,initialize);
    return{tab,topics,topicTotal,topicPage,showCreate,busy,topicForm,topic,showTopic,replies,replyTotal,replyPage,replyBody,contacts,contactTotal,contactPage,peer,showConversation,messages,messageTotal,messagePage,messageBody,canPrivate,canPost,loadTopics,createTopic,loadReplies,openTopic,reply,deleteTopic,deleteReply,loadContacts,loadMessages,openConversation,sendMessage,changeTab};
  }
};
