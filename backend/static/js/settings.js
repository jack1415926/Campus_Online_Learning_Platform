// Exactly two settings, using the existing form and API client.
const PlatformSettingsPage = {
  template:`<el-card><template #header>基础设置</template><el-form label-position="top" style="max-width:480px">
    <el-form-item label="平台名称"><el-input v-model="form.platform_name" maxlength="100"/></el-form-item>
    <el-form-item label="开放学生和教师注册"><el-switch v-model="form.registration_open"/></el-form-item>
    <el-button type="primary" :loading="busy" @click="save">保存设置</el-button>
  </el-form></el-card>`,
  setup(){
    const form=Vue.reactive({platform_name:'',registration_open:true}),busy=Vue.ref(false);
    Vue.onMounted(async()=>{try{Object.assign(form,await api.getPlatformSettings());}catch(e){ElementPlus.ElMessage.error(e.message);}});
    const save=async()=>{busy.value=true;try{const value=await api.savePlatformSettings({...form});Object.assign(form,value);Object.assign(platformState,value);document.title=value.platform_name;ElementPlus.ElMessage.success('设置已保存');}catch(e){ElementPlus.ElMessage.error(e.message);}finally{busy.value=false;}};
    return{form,busy,save};
  }
};
