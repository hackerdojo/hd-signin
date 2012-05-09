var main_screen_turn_on = false;


function capstaff(evt) { 
  var evt = (evt) ? evt : ((event) ? event : null); 
  if (evt.keyCode) code = evt.keyCode;
  else if (evt.which) code = evt.which;  
  var em = $("input[name=email]").val();  
  if (code==45 || code==18) {
    showStaffButtons();
    return false;
  }
  if (code==9 && em.length > 0 && em.indexOf("@") == -1) {
    $("input[name=email]").val(em+"@hackerdojo.com");
    return false;
  }  
}

function autosignin(x) {
  if (x==1) go('Anonymous');
  if (x==2) go('Member');
  if (x==3) go('StaffKey');
  $('#auto').slideUp();  
}


function charge(cc,month,year,first,last) {
 $("input[name=email]").val("");
 $('#ajaxloading').fadeIn();
 $.ajax({
   url: '/api/charge',
   data: 'cc='+cc+'&month='+month+'&year='+year+'&first_name='+first+'&last_name='+last,
   dataType: "json",
   type: "post",
   timeout: 14 * 1000,
   error: function(data) {
     auto_reset();      
     if (data.message) {
       $('#ccerrormessage').html(data.message);
     } else {
       $('#ccerrormessage').html("");
     }
     $('#ajaxloading').hide();
     $('#ccerror').fadeIn();
     setTimeout("$('#ccerror').fadeOut();",3 * 1000);
   },
   success: function(data) {
     if (data.status_code==1) {
       window.audio = new Audio("/static/money.wav");      
       window.audio.play();  
       $('#ajaxloading').fadeOut();
       $('#ccamount').html(data.dollar_amount);
       $('#ccthanksmessage').html(data.message+" #"+data.trans_id);
       $('#ccthanks').fadeIn();
       setTimeout("$('#ccthanks').fadeOut();",6 * 1000);
     } else {
        $('#ccerrormessage').html(data.message);
        $('#ajaxloading').hide();
        $('#ccerror').fadeIn();
        setTimeout("$('#ccerror').fadeOut();",3 * 1000);
     }
   }
  });
}
      
function stopRKey(evt) { 
  var evt = (evt) ? evt : ((event) ? event : null); 
  var node = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null); 
  var em = $("input[name=email]").val();
  
  if (evt.keyCode==45 || evt.keyCode==18) {
    showStaffButtons();
  }
    
  if (evt.keyCode)
    code = evt.keyCode;
  else 
    if (evt.which)
      code = evt.which;

  if (main_screen_turn_on) {
    if (code == 49) go('Anonymous');
    if (code == 50) go('Member');
    if (code == 51) go('StaffKey');
    if (code == 52) cancel();
    return false;
  }
  
  if ((code == 13) && (node.type=="text"))  {    
    
    raw = $("input[name=email]").val();
    
    if (m = raw.match(/^;([0-9]{14,16})=([0-9]{2})([0-9]{2})[0-9]{11}\?/)) {
      var month = m[3];
      var year = m[2];
      var cc = m[1];
      charge(cc,month,year,"","");
      return;
    }
    if (m = raw.match(/^%B([0-9]{14,16})\^(.+)\/(.*)\^([0-9]{2})([0-9]{2}).+\?/)) {
      var month = m[5];
      var year = m[4];
      var first = m[3];
      var last = m[2];
      var cc = m[1];
      charge(cc,month,year, first, last); 
      return;     
    }
    if (m = raw.match(/^[;%]E.*\?/)) {
      // Error
      auto_reset();      
       $('#ccerror').fadeIn();
       $('#ccerrormessage').html("");
       setTimeout("$('#ccerror').fadeOut();",3 * 1000);
       return;      
    }    

    
    entered = $("input[name=email]").val().replace(/^\;/, "").replace(/\?$/, ""); 
   
    /* RFID is numeric */
    if (entered > 0) {
      $("input[name=email]").val("");
      $('#ajaxloading').fadeIn();
      $.ajax({
        url: 'http://signup.hackerdojo.com/api/rfid?id='+entered+'&callback=?',
        dataType: "json",
        timeout: 14 * 1000,
        error: function(data) {
          auto_reset();      
        },
        success: function(data) {
          $('#ajaxloading').fadeOut();
          if (data && data.username) {
            main_screen_turn_on = true;
            // window.audio = new Audio("/static/list.mp3");      
            // window.audio.play();                 
            $('#rfidwelcome').fadeIn();
            $("input[name=email]").val(data.username + "@hackerdojo.com");
            $('.rfidpic').attr("src",data.gravatar);
            $('.rfidname').html(data.name);
            if (data.auto_signin && data.auto_signin > 0 && data.auto_signin < 4) {
              $('#auto').slideDown();
              $('#count').attr("src","/static/countdown.gif");
              window.auto = setTimeout("autosignin("+data.auto_signin+");",5000);
            }
             
          } else {
            prepare_for_signin();
            audio = new Audio("/static/denied.mp3");      
            audio.play();
            $('#denied').fadeIn();
            setTimeout("$('#denied').fadeOut();",3 * 1000);
          }   
        }
      });
        
    }    
    return false;
  } 
} 

function cancel() {
  main_screen_turn_on = false;
  auto_reset();
}

function showStaffButtons() {
	document.getElementById("staffbuttons").style.display="block";
  setTimeout("$('#staffbuttons').show();",30*1000);
}

document.onkeypress = stopRKey; 
document.onkeydown = capstaff; 

String.prototype.capitalize = function(){
   return this.replace( /(^|\s)([a-z])/g , function(m,p1,p2){ return p1+p2.toUpperCase(); } );
};
  
function clickmember() {
  var em = $("input[name=email]").val();  
  if (em.indexOf("@hackerdojo.com")==-1) {
    $("#dojodomain").fadeIn();
    return false;
  } else {
     main_screen_turn_on = true;
     $('#rfidwelcome').show();
     // window.audio = new Audio("/static/list.mp3");      
     // window.audio.play();                 
     name = em.substring(0,em.indexOf("@hackerdojo.com")).replace("."," ").capitalize();
     gravatar = "https://secure.gravatar.com/avatar/" + hex_md5(em);
     $('.rfidpic').attr("src",gravatar);
     $('.rfidname').html(name);
   }  
}

/* Set the type and proceed with signin */
function go(x) {
  if (isEmail($("input[name=email]").val())) {
    document.getElementById("ttt").value = x;
    $('#rfidwelcome').fadeOut();
    $('#ajaxloading').fadeIn();
    main_screen_turn_on = false;
    $('#auto').hide();
    if (window.auto) {
      clearTimeout(window.auto);
    }        
    ok();
  } else {
    alert("Please enter a valid e-mail address");
  }
}

/* Hard reboot */
function auto_reset() {
  $('#tos').hide();
  $('#thanks').fadeOut();
  $('#denied').fadeOut();
  $('#privacy').hide();
  $('#auto').hide();
  $('#rfidwelcome').fadeOut();
  $('#ajaxloading').fadeOut();
  if (window.auto) {
    clearTimeout(window.auto);
  }    
  main_screen_turn_on = false;
  prepare_for_signin();
}

/* Soft reboot */
function prepare_for_signin() {
  $("#staffbuttons").hide();
  $('#ttt').val("");
  $('#em').val("");
  $("input[type=text]").val("");
  $('input[name=email]').focus();
}
  
/* Do the actual signin */  
function ok() {
  $("#tos").fadeOut();
  main_screen_turn_on = false;
  $('#ajaxloading').show();
  $.ajax({
    url: '/signin',
    dataType: "json",
    data: $('#ajax_form').serialize(),
    timeout: 14 * 1000,
    error: function(data) {
      auto_reset();      
    },
    success: function(data) {
      $('#ajaxloading').fadeOut();
      $("#thanksmessage").html("<b><nobr>Thanks "+data.name+"!</nobr></b><br/><br/><small>Visit #"+data.signins+"</small>");      
      if (data.tos) {
        $('#ajaxloading').hide();
        $('#tos').fadeIn();
      } else {        
        thanks();
      }
      prepare_for_signin();
    }
  });
}

/* After a user signs in */
function thanks() {
  $("#banner").hide().fadeIn(1500);
  $("#tos").hide();
  $("#thanks").fadeIn();
  window.audio = new Audio("/static/login.mp3");      
  window.audio.play();
  increment_counter();
  setTimeout('$("#thanks").fadeOut(1000);',2*1000);
  $('input[name=email]').focus();
}

function increment_counter() {
  var i = parseInt($("#todaycount").html());
  if (i>0) {
    $("#todaycount").html(i+1);
  }
}

function isEmail (s) {
  return String(s).search (/^\s*[\w\-\+_]+(\.[\w\-\+_]+)*\@[\w\-\+_]+\.[\w\-\+_]+(\.[\w\-\+_]+)*\s*$/) != -1;
}

/* Refresh the page every 15 minutes to clean things up, and update banner */
function refreshPage() {
  $.ajax({
    url: '/',
    success: function(data) {
      if (window.oldint) {
        clearTimeout(window.oldint);
      }      
      if (window.oldfoc) {
        clearTimeout(window.oldfoc);
      }      
      $('#body').html(data);
    }
  });
  auto_reset();
}

$(document).ready(function() {
  window.oldint = setInterval(refreshPage,15 *60* 1000);  
  window.oldfoc = setInterval('$("#em").focus();',1000);
  auto_reset();
  
  $("#em").live('blur', function() {
    setTimeout('$("#em").focus();',16);
  });
  
          
});


