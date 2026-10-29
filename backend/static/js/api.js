// LMS API Client
const API_BASE = "/api/v1";

const api = {
  _session: Vue.reactive({ token: localStorage.getItem("lms_token") || "" }),
  getToken() { return this._session.token; },
  setToken(token) { localStorage.setItem("lms_token", token); this._session.token = token; },
  clearToken() { localStorage.removeItem("lms_token"); this._session.token = ""; this._perms = []; this._user = null; },
  // Permission storage
  _perms: null,
  _user: null,
  hasRole(role) { return (this._user?.roles || []).includes(role); },
  setPerms(perms) { this._perms = perms || []; },
  hasPerm(perm) { if (!this._perms) return false; if (this._perms.includes("system:config")) return true; return this._perms.includes(perm); },
  hasAnyPerm(...perms) { if (!this._perms) return false; if (this._perms.includes("system:config")) return true; return perms.some(p => this._perms.includes(p)); },
  isLoggedIn() { return !!this.getToken(); },
  async request(method, path, data = null, isForm = false) {
    const headers = {};
    if (!isForm) headers["Content-Type"] = "application/json";
    const token = this.getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    const opts = { method, headers };
    if (data) opts.body = isForm ? data : JSON.stringify(data);
    const resp = await fetch(API_BASE + path, opts);
    if (resp.status === 204) return null;
    const text = await resp.text();
    let json = null;
    try { json = JSON.parse(text); } catch(e) { json = text; }
    if (resp.status === 401) {
      // Session invalid: clear token and redirect to login with a reason
      this.clearToken();
      let reason = "Unauthorized";
      if (json && json.detail) reason = typeof json.detail === "string" ? json.detail : "Unauthorized";
      // Avoid redirecting repeatedly when already on the login page
      if (!window.location.hash.includes("#login")) {
        try {
          if (window.ElMessage) {
            if (reason.indexOf("\u5df2\u5728\u5176\u4ed6\u8bbe\u5907\u767b\u5f55") !== -1) {
              window.ElMessage.error("\u8be5\u8d26\u53f7\u5df2\u5728\u5176\u4ed6\u8bbe\u5907\u767b\u5f55\uff0c\u60a8\u5df2\u88ab\u5f3a\u5236\u4e0b\u7ebf\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55");
            } else if (reason.indexOf("\u767b\u5f55\u4f1a\u8bdd\u5df2\u8d85\u65f6") !== -1) {
              window.ElMessage.warning("\u767b\u5f55\u5df2\u8d85\u65f6\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55");
            } else {
              window.ElMessage.warning("\u8bf7\u5148\u767b\u5f55");
            }
          }
        } catch(e) {}
        window.location.hash = "#login";
      }
      throw new Error(reason);
    }
    if (!resp.ok) {
      const detail = json && json.detail;
      const fields = {email:'邮箱',username:'用户名',password:'密码',full_name:'姓名',old_password:'原密码',new_password:'新密码'};
      const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? [...new Set(detail.map(error => {
        const field = error.loc?.at(-1);
        if (field === 'email') return '邮箱格式不正确';
        return (fields[field] || '提交内容') + '填写不正确，请检查后重试';
      }))].join('；') : '请求失败，请稍后重试';
      throw new Error(msg);
    }
    return json;
  },
  // Auth
  getPlatformSettings(){return this.request('GET','/platform-settings');},
  savePlatformSettings(body){return this.request('PUT','/platform-settings',body);},
  certificateStatus(courseId){return this.request('GET',`/courses/${courseId}/certificate`);},
  claimCertificate(courseId){return this.request('POST',`/courses/${courseId}/certificate`);},
  courseCertificates(courseId,page=1){return this.request('GET',`/courses/${courseId}/certificates?page=${page}`);},
  login(body) { return this.request("POST", "/auth/login", body); },
  register(body) { return this.request("POST", "/auth/register", body); },
  listTopics(courseId,page=1){return this.request('GET',`/courses/${courseId}/discussions?page=${page}`);},
  createTopic(courseId,body){return this.request('POST',`/courses/${courseId}/discussions`,body);},
  getTopic(courseId,id,page=1){return this.request('GET',`/courses/${courseId}/discussions/${id}?page=${page}`);},
  replyTopic(courseId,id,body){return this.request('POST',`/courses/${courseId}/discussions/${id}/replies`,body);},
  deleteTopic(courseId,id){return this.request('DELETE',`/courses/${courseId}/discussions/${id}`);},
  deleteReply(courseId,id,replyId){return this.request('DELETE',`/courses/${courseId}/discussions/${id}/replies/${replyId}`);},
  privateContacts(courseId,page=1){return this.request('GET',`/courses/${courseId}/private-contacts?page=${page}`);},
  conversation(courseId,peerId,page=1){return this.request('GET',`/courses/${courseId}/messages?peer_id=${encodeURIComponent(peerId)}&page=${page}`);},
  sendMessage(courseId,body){return this.request('POST',`/courses/${courseId}/messages`,body);},
  logout() { return this.request("POST", "/auth/logout"); },
  getMe() { return this.request("GET", "/auth/me").then(u => { this.setPerms(u.permissions || []); this._user=u; return u; }); },
  // Users
  getProfile() { return this.request("GET", "/users/me/profile"); },
  updateProfile(body) { return this.request("PUT", "/users/me/profile", body); },
  changePassword(body) { return this.request("POST", "/users/me/password", body); },
  reviewTeacher(id, body) { return this.request("POST", "/users/"+id+"/teacher-review", body); },
  setUserStatus(id, body) { return this.request("PUT", "/users/"+id+"/status", body); },
  listUsers(params) { const q = params ? "?" + new URLSearchParams(params).toString() : ""; return this.request("GET", "/users" + q); },
  createUser(body) { return this.request("POST", "/users", body); },
  updateUser(id, body) { return this.request("PUT", "/users/" + id, body); },
  deleteUser(id) { return this.request("DELETE", "/users/" + id); },
  assignRole(userId, body) { return this.request("POST", "/users/" + userId + "/roles", body); },
  // Categories
  listCategories() { return this.request("GET", "/categories"); },
  createCategory(body) { return this.request("POST", "/categories", body); },
  updateCategory(id, body) { return this.request("PUT", "/categories/" + id, body); },
  deleteCategory(id) { return this.request("DELETE", "/categories/" + id); },
  // Tags
  listTags() { return this.request("GET", "/tags"); },
  createTag(body) { return this.request("POST", "/tags", body); },
  deleteTag(id) { return this.request("DELETE", "/tags/" + id); },
  // Media
  listMedia(params) { const q = params ? "?" + new URLSearchParams(params).toString() : ""; return this.request("GET", "/media" + q); },
  getMedia(id) { return this.request("GET", "/media/" + id); },
  uploadMedia(file, params, onProgress) {
    const fd = new FormData(); fd.append("file", file);
    const q = params ? "?" + new URLSearchParams(params).toString() : "";
    const token = this.getToken();
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", API_BASE + "/media/upload" + q);
      if (token) xhr.setRequestHeader("Authorization", "Bearer " + token);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
      };
      xhr.onload = () => {
        let body = null;
        try { body = JSON.parse(xhr.responseText); } catch(e) { body = xhr.responseText; }
        if (xhr.status >= 200 && xhr.status < 300) { resolve(body); return; }
        let msg = "上传失败";
        if (body && body.detail) msg = typeof body.detail === "string" ? body.detail : msg;
        const err = new Error(msg);
        err.status = xhr.status;
        reject(err);
      };
      xhr.onerror = () => reject(new Error("网络错误，上传失败"));
      xhr.send(fd);
    });
  },
  deleteMedia(id) { return this.request("DELETE", "/media/" + id); },
  getMediaUrl(id) { return this.request("GET", "/media/" + id + "/url"); },
  // Media Categories
  listMediaCategories() { return this.request("GET", "/media/categories"); },
  createMediaCategory(body) { return this.request("POST", "/media/categories", body); },
  updateMediaCategory(id, body) { return this.request("PUT", "/media/categories/" + id, body); },
  deleteMediaCategory(id) { return this.request("DELETE", "/media/categories/" + id); },
  // Courses
  listCourses(params) { const q = params ? "?" + new URLSearchParams(params).toString() : ""; return this.request("GET", "/courses" + q); },
  getCourse(id) { return this.request("GET", "/courses/" + id); },
  createCourse(body) { return this.request("POST", "/courses", body); },
  updateCourse(id, body) { return this.request("PUT", "/courses/" + id, body); },
  deleteCourse(id) { return this.request("DELETE", "/courses/" + id); },
  publishCourse(id, action, reason="") { return this.request("POST", "/courses/" + id + "/publish", { action, reason }); },
  joinCourse(id) { return this.request("POST", "/courses/" + id + "/join"); },
  addChapter(courseId, body) { return this.request("POST", "/courses/" + courseId + "/chapters", body); },
  updateChapter(courseId, chId, body) { return this.request("PUT", "/courses/" + courseId + "/chapters/" + chId, body); },
  deleteChapter(courseId, chId) { return this.request("DELETE", "/courses/" + courseId + "/chapters/" + chId); },
  // Learning
  listPlans(params) { const q = params ? "?" + new URLSearchParams(params).toString() : ""; return this.request("GET", "/learning/plans" + q); },
  createPlan(body) { return this.request("POST", "/learning/plans", body); },
  deletePlan(id) { return this.request("DELETE", "/learning/plans/" + id); },
  listPaths(params) { const q = params ? "?" + new URLSearchParams(params).toString() : ""; return this.request("GET", "/learning/paths" + q); },
  createPath(body) { return this.request("POST", "/learning/paths", body); },
  deletePath(id) { return this.request("DELETE", "/learning/paths/" + id); },
  createAssignment(body) { return this.request("POST", "/learning/assignments", body); },
  listAssignments(params) { const q = params ? "?" + new URLSearchParams(params).toString() : ""; return this.request("GET", "/learning/assignments" + q); },
  getMyAssignments() { return this.request("GET", "/learning/my-assignments"); },
  updateProgress(body) { return this.request("POST", "/learning/progress", body); },
  getCourseProgress(courseId) { return this.request("GET", "/learning/progress/" + courseId); },
  resetCourseProgress(courseId) { return this.request("POST", "/learning/reset/" + courseId); },
  getMyRecords(courseId) { return this.request("GET", "/learning/records" + (courseId ? "?course_id=" + encodeURIComponent(courseId) : "")); },
  listHomeworks(courseId, page=1) { return this.request("GET", `/courses/${courseId}/homeworks?page=${page}`); },
  saveHomework(courseId, id, body) { return this.request(id ? "PUT" : "POST", `/courses/${courseId}/homeworks`+(id?`/${id}`:""), body); },
  deleteHomework(courseId, id) { return this.request("DELETE", `/courses/${courseId}/homeworks/${id}`); },
  submitHomework(courseId, id, form) { return this.request("PUT", `/courses/${courseId}/homeworks/${id}/submission`, form, true); },
  homeworkSubmissions(courseId, id, page=1) { return this.request("GET", `/courses/${courseId}/homeworks/${id}/submissions?page=${page}`); },
  gradeHomework(courseId, id, submissionId, body) { return this.request("POST", `/courses/${courseId}/homeworks/${id}/submissions/${submissionId}/grade`, body); },
  courseStudents(courseId, page=1) { return this.request("GET", `/learning/courses/${courseId}/students?page=${page}`); },
  async downloadHomework(courseId, id, submission) {
    const response=await fetch(`${API_BASE}/courses/${courseId}/homeworks/${id}/submissions/${submission.id}/attachment`,{headers:{Authorization:"Bearer "+this.getToken()}});
    if(!response.ok){const body=await response.json();throw new Error(body.detail||"下载失败");}
    const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download=submission.attachment_name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  },
  getResume(courseId) { return this.request("GET", "/learning/resume/" + courseId); },
  // Notifications
  listNotifications(params) { const q = params ? "?" + new URLSearchParams(params).toString() : ""; return this.request("GET", "/notifications" + q); },
  getUnreadCount() { return this.request("GET", "/notifications/unread-count"); },
  markRead(ids) { return this.request("PUT", "/notifications/read", { notification_ids: ids }); },
  markAllRead() { return this.request("PUT", "/notifications/read-all"); },
  listTemplates() { return this.request("GET", "/notifications/templates"); },
  createTemplate(body) { return this.request("POST", "/notifications/templates", body); },
  deleteTemplate(id) { return this.request("DELETE", "/notifications/templates/" + id); },
  sendNotification(body) { return this.request("POST", "/notifications/send", body); },
  // Exams
  listQuestions(params) { const q = params ? "?" + new URLSearchParams(params).toString() : ""; return this.request("GET", "/exams/questions" + q); },
  createQuestion(body) { return this.request("POST", "/exams/questions", body); },
  updateQuestion(id, body) { return this.request("PUT", "/exams/questions/"+id, body); },
  batchImportQuestions(items) { return this.request("POST", "/exams/questions/batch", items); },
  deleteQuestion(id) { return this.request("DELETE", "/exams/questions/" + id); },
  // Question Banks
  listQuestionBanks() { return this.request("GET", "/exams/question-banks"); },
  createQuestionBank(body) { return this.request("POST", "/exams/question-banks", body); },
  updateQuestionBank(id, body) { return this.request("PUT", "/exams/question-banks/" + id, body); },
  deleteQuestionBank(id) { return this.request("DELETE", "/exams/question-banks/" + id); },
  importQuestions(bankId, file) {
    const formData = new FormData();
    formData.append("file", file);
    return this.request("POST", "/exams/question-banks/" + bankId + "/import", formData, true);
  },
  getQuestionBankTemplateUrl() { return this.baseUrl + "/exams/question-banks/template"; },
  listExams(params) { const q = params ? "?" + new URLSearchParams(params).toString() : ""; return this.request("GET", "/exams" + q); },
  getExam(id) { return this.request("GET", "/exams/" + id); },
  createExam(body) { return this.request("POST", "/exams", body); },
  saveExam(id, body) { return this.request(id?"PUT":"POST", "/exams"+(id?"/"+id:""), body); },
  examRecords(id, page=1) { return this.request("GET", `/exams/${id}/records?page=${page}`); },
  saveExamDraft(id, body) { return this.request("PUT", `/exams/records/${id}/draft`, body); },
  deleteExam(id) { return this.request("DELETE", "/exams/" + id); },
  startExam(id) { return this.request("POST", "/exams/" + id + "/start"); },
  submitExam(recordId, body) { return this.request("POST", "/exams/records/" + recordId + "/submit", body); },
  getExamRecord(id) { return this.request("GET", "/exams/records/" + id); },
  getMyExamRecords(examId) { return this.request("GET", "/exams/records/my"+(examId?"?exam_id="+encodeURIComponent(examId):"")); },
  getWrongQuestions(params) {
    if (!params) return this.request("GET", "/exams/wrong-questions");
    const q = new URLSearchParams();
    if (params.exam_id) q.set("exam_id", params.exam_id);
    if (params.question_bank_id) q.set("question_bank_id", params.question_bank_id);
    return this.request("GET", "/exams/wrong-questions?" + q.toString());
  },
  gradeExam(recordId, body) { return this.request("POST", "/exams/records/" + recordId + "/grade", body); },
  getExamAnalysis(examId) { return this.request("GET", "/exams/" + examId + "/analysis"); },
  // Reports
  getPersonalReport() { return this.request("GET", "/reports/personal"); },
  getComplianceReport() { return this.request("GET", "/reports/compliance"); },
  getCourseReport(courseId) { return this.request("GET", "/reports/course/" + courseId); },
  getDeptReport(deptId) { return this.request("GET", "/reports/department/" + deptId); },
  getPlanReport(planId) { return this.request("GET", "/reports/plan/" + planId); },
  // Job levels
  listJobLevels() { return this.request("GET", "/job-levels"); },
  createJobLevel(body) { return this.request("POST", "/job-levels", body); },
  updateJobLevel(id, body) { return this.request("PUT", "/job-levels/" + id, body); },
  deleteJobLevel(id) { return this.request("DELETE", "/job-levels/" + id); },
  // Positions
  listPositions() { return this.request("GET", "/positions"); },
  createPosition(body) { return this.request("POST", "/positions", body); },
  updatePosition(id, body) { return this.request("PUT", "/positions/" + id, body); },
  deletePosition(id) { return this.request("DELETE", "/positions/" + id); },
  // Departments
  listDepartments() { return this.request("GET", "/departments"); },
  createDepartment(body) { return this.request("POST", "/departments", body); },
  updateDepartment(id, body) { return this.request("PUT", "/departments/" + id, body); },
  deleteDepartment(id) { return this.request("DELETE", "/departments/" + id); },
};
