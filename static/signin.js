var main_screen_turn_on = false;

function capstaff(evt) { 
  var evt = (evt) ? evt : ((event) ? event : null); 
  if (evt.keyCode) code = evt.keyCode;
  else if (evt.which) code = evt.which;  
  var em = document.getElementById("em").value;  
  if (code==45 || code==18) {
    showStaffButtons();
    return false;
  }
  if (code==9 && em.length>0 && em.indexOf("@")==-1) {
    document.getElementById("em").value = em+"@hackerdojo.com";
    return false;
  }  
}

function stopRKey(evt) { 
  var evt = (evt) ? evt : ((event) ? event : null); 
  var node = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null); 
  var em = document.getElementById("em").value;
  
  if (evt.keyCode==45 || evt.keyCode==18) {
    showStaffButtons();
  }
    
  if (evt.keyCode) code = evt.keyCode;
  else if (evt.which) code = evt.which;

  if (main_screen_turn_on) {
   if (code == 49) go('Anonymous',true);
   if (code == 50) go('Member',true);
   if (code == 51) go('StaffKey',true);
   if (code == 52) cancel();
   return false;
  }
  if ((code == 13) && (node.type=="text"))  {    
    entered = document.getElementById("em").value;
    /* RFID is numeric */
    if (entered > 0) {
      document.getElementById("em").value = "";
      $('#ajaxloading').show();
      $.getJSON( 'http://signup.hackerdojo.com/api/rfid?id='+entered+'&callback=?', '',
        function (data) { 
          $('#ajaxloading').hide();
          if (data && data.username) {
            main_screen_turn_on = true;
            $('#rfidwelcome').show();
            document.getElementById("em").value = data.username + "@hackerdojo.com";
            $('.rfidpic').attr("src",data.gravatar);
            $('.rfidname').html(data.name);
            // setTimeout('auto_reset();',90000);
          } else {
            $('#denied').show();
            setTimeout("auto_reset();",3 * 1000);
          }   
        } 
      );
    }    
    return false;
  } 

} 

function cancel() {
  $('#ajaxloading').hide();
  $('#rfidwelcome').hide();
  main_screen_turn_on = false;
  document.getElementById("em").value = "";
  document.getElementById("em").focus();
}

function showStaffButtons() {
	document.getElementById("staffbuttons").style.display="block";
    setTimeout("document.getElementById('staffbuttons').style.display='none';",30*1000);
}

document.onkeypress = stopRKey; 
document.onkeydown = capstaff; 

String.prototype.capitalize = function(){
   return this.replace( /(^|\s)([a-z])/g , function(m,p1,p2){ return p1+p2.toUpperCase(); } );
};
  
function clickmember() {
  var em = document.getElementById("em").value;  
  if (em.indexOf("@hackerdojo.com")==-1) {
    alert("That e-mail address does not match a valid @hackerdojo.com e-mail.");   
    return false;
  } else {
     main_screen_turn_on = true;
     em.value
     $('#rfidwelcome').show();
     name = em.substring(0,em.indexOf("@hackerdojo.com")).replace("."," ").capitalize();
     gravatar = "http://www.gravatar.com/avatar/" + hex_md5(em);
     $('.rfidpic').attr("src",gravatar);
     $('.rfidname').html(name);
   }  
}

function auto_reset() {
  $('#tos').hide();
  $('#thanks').hide();
  $('#denied').hide();
  $('#privacy').hide();
  $('#rfidwelcome').hide();
  $('#ajaxloading').hide();
  main_screen_turn_on = false;
  document.getElementById("ttt").value = "";
  document.getElementById("em").value = "";
  document.getElementById("em").focus();
}

function go(x,skip) {
  if (isEmail(document.getElementById("em").value)) {
    document.getElementById("ttt").value = x;
    if (skip) {
      $('#rfidwelcome').hide();
      $('#ajaxloading').show();
      main_screen_turn_on = false;
      document.getElementById("f").submit();
    } else {
      document.getElementById("tos").style.display = 'block';
      setTimeout('auto_reset()',5*60*1000);
    }
  } else {
    alert("Please enter a valid e-mail address");
  }
}

function ok() {
  document.getElementById("tos").style.display = 'none';
  document.getElementById("thanks").style.display = 'block';
  main_screen_turn_on = false;
  setTimeout('document.getElementById("f").submit();',1000);
}

function isEmail (s) {
  return String(s).search (/^\s*[\w\-\+_]+(\.[\w\-\+_]+)*\@[\w\-\+_]+\.[\w\-\+_]+(\.[\w\-\+_]+)*\s*$/) != -1;
}

$(document).ready(function() {
  $("#em").value = "";
  $("#em").focus();
});
