(function(){
  document.addEventListener('htmx:configRequest', function(evt){
    try {
      var token = localStorage.getItem('sb:token') || (document.cookie.match(/(?:^|; )sb-access-token=([^;]*)/)||[])[1];
      if (token) {
        evt.detail.headers['Authorization'] = 'Bearer ' + decodeURIComponent(token);
      }
    } catch(e) {}
  });
})();
