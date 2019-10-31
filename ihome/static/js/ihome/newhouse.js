function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(document).ready(function(){
    // $('.popup_con').fadeIn('fast');
    // $('.popup_con').fadeOut('fast');
    // 向后端获取城区信息
    $.get("/api/v1.0/areas",function (resp) {
        if (resp.errno=="0") {
             var areas = resp.data;
             //使用js模板
             var html = template("areas-tmpl",{areas:areas});
             $("#area-id").html(html);
        } else {
             alert(resp.errmsg);
        }
    },"json");
})