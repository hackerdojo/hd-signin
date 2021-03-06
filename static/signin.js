var main_screen_turn_on = false;


function capstaff(evt) {
    var evt = (evt) ? evt : ((event) ? event : null);
    if (evt.keyCode) code = evt.keyCode;
    else if (evt.which) code = evt.which;
    var em = $("input[name=email]").val();
    if (code == 9 && em.length > 0 && em.indexOf("@") == -1) {
        $("input[name=email]").val(em + "@hackerdojo.com");
        return false;
    }
}

function stopRKey(evt) {
    var evt = (evt) ? evt : ((event) ? event : null);
    var node = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
    var em = $("input[name=email]").val();

    if (evt.keyCode) {
        code = evt.keyCode;
    } else {
        if (evt.which) {
            code = evt.which;
        }
    }

    if (main_screen_turn_on) {
        if (code == 49) go('Anonymous');
        if (code == 50) go('Member');
        if (code == 52) cancel();
        return false;
    }

    if (code === 37 || code === 59) {
        // if the input is either a semicolon or percent sign, make input field font white
        $("input[name=email]").css('font-color', '#fff');
    }

    if ((code == 13) && (node.type == "text")) {
        setTimeout(function () {
            $("input[name=email]").css('font-color', '#000');
        }, 1000);

        raw = $("input[name=email]").val();

        if (m = raw.match(/^;([0-9]{14,16})=([0-9]{2})([0-9]{2})[0-9]{11}\?/)) {
            var month = m[3];
            var year = m[2];
            var cc = m[1];
            charge(cc, month, year, "", "");
            return;
        }
        if (m = raw.match(/^%B([0-9]{14,16})\^(.+)\/(.*)\^([0-9]{2})([0-9]{2}).+\?/)) {
            var month = m[5];
            var year = m[4];
            var first = m[3];
            var last = m[2];
            var cc = m[1];
            charge(cc, month, year, first, last);
            return;
        }
        if (m = raw.match(/^[;%]E.*\?/)) {
            // Error
            auto_reset();
            $('#error_title').html('Credit Card Error');
            $('#error_message').html('');
            $('#error').fadeIn();
            setTimeout("$('#error').fadeOut();", 3 * 1000);
            return;
        }

        if (window.cconly) {
            auto_reset();
            $('#error_title').html('Credit Card Error');
            $('#error_message').html('');
            $('#error').fadeIn();
            setTimeout("$('#error').fadeOut();", 3 * 1000);
            return;
        }

        entered = $("input[name=email]").val().replace(/^\;/, "").replace(/\?$/, "");

        /* RFID is numeric */
        if (entered > 0) {
            $("input[name=email]").val("");
            $('#ajaxloading').fadeIn();
            $.ajax({
                url: 'rfid/' + entered,
                dataType: "json",
                timeout: 14 * 1000,
                error: function (jqXHR, textStatus, errorThrown) {
                    $('#ajaxloading').fadeOut();
                    $('#error_title').html('<b>Signin Error</b>');
                    $('#error_message').html(errorThrown);
                    $('#error').fadeIn();
                },
                success: function (data) {
                    $('#ajaxloading').fadeOut();
                    if (data.status == "upgrade") {
                        // User needs to upgrade.
                        $('#upgrade').fadeIn();
                    } else if (!data.bad_key) {
                        // We're signed in.
                        var visit_message = 'Visit #' + data.signins;
                        if (data.visits_remaining) {
                            visit_message = data.visits_remaining + ' visits remaining' +
                                ' this month.';
                        }

                        thanks(data.name, visit_message);
                    } else {
                        prepare_for_signin();
                        audio = new Audio("/static/denied.mp3");
                        audio.play();
                        $('#error_title').html('Access Denied');
                        $('#error_message').html('Invalid RFID key.');
                        $('#error').fadeIn();
                        setTimeout("$('#error').fadeOut();", 3 * 1000);
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

document.onkeypress = stopRKey;
document.onkeydown = capstaff;

String.prototype.capitalize = function () {
    return this.replace(/(^|\s)([a-z])/g, function (m, p1, p2) {
        return p1 + p2.toUpperCase();
    });
};

// function clickmember() {
//   var em = $("input[name=email]").val();
//   if (em.indexOf("@hackerdojo.com")==-1) {
//     $("#dojodomain").fadeIn();
//     return false;
//   } else {
//      main_screen_turn_on = true;
//      $('#rfidwelcome').show();
//      name = em.substring(0,em.indexOf("@hackerdojo.com")).replace("."," ").capitalize();
//      gravatar = "https://secure.gravatar.com/avatar/" + hex_md5(em);
//      $('.rfidpic').attr("src",gravatar);
//      $('.rfidname').html(name);
//    }
// }

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
    $('#error').fadeOut();
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
        error: function (jqXHR, textStatus, errorThrown) {
            $('#ajaxloading').fadeOut();
            $('#error_title').html('<b>Signin Error</b>');
            $('#error_message').html(errorThrown);
            $('#error').fadeIn();
        },
        success: function (data) {
            $('#ajaxloading').fadeOut();

            if (data.nomember) {
                $('#error_title').html('<b>Access Denied</b>');
                $('#error_message').html('You are not an active member. ' +
                    'Please sign up, or reactivate ' +
                    'your account. If you believe this ' +
                    'message is in error, check the email ' +
                    'address that you entered.');
                $('#error').fadeIn();
            } else if (data.status == "upgrade") {
                $('#upgrade').fadeIn();
            } else {
                var visit_message = 'Visit #' + data.signins;
                if (data.visits_remaining) {
                    visit_message = data.visits_remaining + ' visits remaining' +
                        ' this month.';
                }

                if (data.tos) {
                    $('#ajaxloading').hide();
                    $('#tos').fadeIn();
                } else {
                    thanks(data.name, visit_message);
                }
            }
            prepare_for_signin();
        }
    });
}

/* After a user signs in */
function thanks(name, visit_message) {
    $("#banner").hide().fadeIn(1500);
    $("#tos").hide();

    $("#thanksmessage").html('<b><nobr>Thanks ' + name + '!' +
        '</nobr></b><br/><br/><small>' + visit_message
        + '</small>');

    $("#thanks").fadeIn();
    window.audio = new Audio("/static/login.mp3");
    window.audio.play();
    increment_counter();
    setTimeout('$("#thanks").fadeOut(1000);', 3 * 1000);
    $('input[name=email]').focus();
}

/* Close all popup windows. */
function close_popups() {
    $('#error').fadeOut();
    $('#thanks').fadeOut();
    $('#upgrade').fadeOut();
    prepare_for_signin();
}

function increment_counter() {
    var i = parseInt($("#todaycount").html());
    if (i > 0) {
        $("#todaycount").html(i + 1);
    }
}

function isEmail(s) {
    return String(s).search(/^\s*[\w\-\+_]+(\.[\w\-\+_]+)*\@[\w\-\+_]+\.[\w\-\+_]+(\.[\w\-\+_]+)*\s*$/) != -1;
}

/* Refresh the page every 15 minutes to clean things up, and update banner */
function refreshPage() {
    $.ajax({
        url: window.cconly ? '/cc' : '/',
        success: function (data) {
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

$(document).ready(function () {
    window.oldfoc = setInterval('$("#em").focus();', 1000);
    auto_reset();

    $('#error').click(close_popups);
    $('#upgrade').click(close_popups);
});


