/* =========================================
   RENT & GO AUTHENTICATION
========================================= */


/* Store current authentication type */

let authType = "signup";


/* Demo OTP */

let demoOTP = "123456";


/* =========================================
   OPEN AUTH PAGE
========================================= */

function openAuth(type) {

    window.location.href =
        "auth.html?mode=" + type;

}


/* =========================================
   WHEN AUTH PAGE LOADS
========================================= */

document.addEventListener("DOMContentLoaded", function () {

    const params =
        new URLSearchParams(window.location.search);

    const mode =
        params.get("mode");


    if (mode === "login") {

        showLogin();

    }

    else {

        showSignup();

    }


    setupOTPInputs();

});


/* =========================================
   SHOW LOGIN
========================================= */

function showLogin() {

    authType = "login";

    hideAllPages();

    document
        .getElementById("loginPage")
        .classList.remove("hidden");

}


/* =========================================
   SHOW SIGNUP
========================================= */

function showSignup() {

    authType = "signup";

    hideAllPages();

    document
        .getElementById("signupPage")
        .classList.remove("hidden");

}


/* =========================================
   HIDE ALL
========================================= */

function hideAllPages() {

    const pages = document.querySelectorAll(".auth-page");

    pages.forEach(function(page) {

        page.classList.add("hidden");

    });

}


/* =========================================
   VALIDATE MOBILE
========================================= */

function validMobile(number) {

    return /^[6-9][0-9]{9}$/.test(number);

}


/* =========================================
   LOGIN OTP
========================================= */

function sendLoginOTP() {

    const mobile =
        document
        .getElementById("loginMobile")
        .value.trim();


    if (!validMobile(mobile)) {

        alert(
            "Please enter a valid 10-digit Indian mobile number."
        );

        return;

    }


    sendOTP(mobile);

}


/* =========================================
   SIGNUP OTP
========================================= */

function sendSignupOTP() {

    const mobile =
        document
        .getElementById("signupMobile")
        .value.trim();


    if (!validMobile(mobile)) {

        alert(
            "Please enter a valid 10-digit Indian mobile number."
        );

        return;

    }


    sendOTP(mobile);

}


/* =========================================
   SEND OTP
========================================= */

function sendOTP(mobile) {

    /*
        DEMO ONLY

        In the real application this function
        will call your backend API.

        Example:

        fetch("/api/send-otp", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                mobile: mobile
            })
        });
    */


    demoOTP =
        Math.floor(
            100000 +
            Math.random() * 900000
        ).toString();


    console.log(
        "DEMO OTP:",
        demoOTP
    );


    document
        .getElementById("otpMobile")
        .textContent =
        "+91 " + mobile;


    hideAllPages();

    document
        .getElementById("otpPage")
        .classList.remove("hidden");


    startTimer();

}


/* =========================================
   OTP INPUT
========================================= */

function setupOTPInputs() {

    const inputs =
        document.querySelectorAll(".otp");


    inputs.forEach(function(input, index) {


        input.addEventListener(
            "input",
            function () {

                if (
                    input.value.length === 1 &&
                    index < inputs.length - 1
                ) {

                    inputs[index + 1].focus();

                }

            }
        );


        input.addEventListener(
            "keydown",
            function(event) {

                if (
                    event.key === "Backspace" &&
                    input.value === "" &&
                    index > 0
                ) {

                    inputs[index - 1].focus();

                }

            }
        );

    });

}


/* =========================================
   GET OTP VALUE
========================================= */

function getOTP() {

    const inputs =
        document.querySelectorAll(".otp");

    let otp = "";

    inputs.forEach(function(input) {

        otp += input.value;

    });

    return otp;

}


/* =========================================
   VERIFY OTP
========================================= */

function verifyOTP() {

    const enteredOTP =
        getOTP();


    const message =
        document.getElementById("otpMessage");


    if (enteredOTP.length !== 6) {

        message.textContent =
            "Please enter the complete 6-digit OTP.";

        message.style.color = "red";

        return;

    }


    if (enteredOTP === demoOTP) {

        message.textContent =
            "Mobile number verified successfully!";

        message.style.color =
            "#159447";


        setTimeout(function() {

            if (authType === "signup") {

                showProfile();

            }

            else {

                /*
                    Login user.

                    Real application:
                    send authentication token
                    and redirect to dashboard.
                */

                goHome();

            }

        }, 800);

    }

    else {

        message.textContent =
            "Incorrect OTP. Please try again.";

        message.style.color =
            "red";

    }

}


/* =========================================
   TIMER
========================================= */

let timerInterval;


function startTimer() {

    clearInterval(timerInterval);


    let seconds = 45;


    const timer =
        document.getElementById("timer");


    timer.textContent =
        "00:45";


    timerInterval =
        setInterval(function() {

            seconds--;


            let formatted =
                seconds < 10
                ? "0" + seconds
                : seconds;


            timer.textContent =
                "00:" + formatted;


            if (seconds <= 0) {

                clearInterval(timerInterval);

                timer.textContent =
                    "Resend";

            }

        }, 1000);

}


/* =========================================
   BACK TO MOBILE
========================================= */

function backToNumber() {

    if (authType === "signup") {

        showSignup();

    }

    else {

        showLogin();

    }

}


/* =========================================
   PROFILE
========================================= */

function showProfile() {

    hideAllPages();

    document
        .getElementById("profilePage")
        .classList.remove("hidden");

}


/* =========================================
   CREATE ACCOUNT
========================================= */

function createAccount() {

    const name =
        document
        .getElementById("fullName")
        .value.trim();


    const email =
        document
        .getElementById("email")
        .value.trim();


    const password =
        document
        .getElementById("password")
        .value;


    const role =
        document
        .getElementById("role")
        .value;


    if (name.length < 3) {

        alert(
            "Please enter your full name."
        );

        return;

    }


    if (
        email !== "" &&
        !email.includes("@")
    ) {

        alert(
            "Please enter a valid email."
        );

        return;

    }


    if (password.length < 8) {

        alert(
            "Password must contain at least 8 characters."
        );

        return;

    }


    /*
        Create unique Rent&Go ID

        Example:

        RG + 6 random digits
    */

    const userID =
        "RG" +
        Math.floor(
            100000 +
            Math.random() * 900000
        );


    document
        .getElementById("userID")
        .textContent =
        userID;


    /*
        Store demo user locally.

        IMPORTANT:
        Do NOT store passwords like this
        in a real application.

        Real passwords must be hashed
        on the backend.
    */

    const user = {

        id: userID,

        name: name,

        email: email,

        role: role

    };


    localStorage.setItem(
        "rentgoUser",
        JSON.stringify(user)
    );


    hideAllPages();

    document
        .getElementById("successPage")
        .classList.remove("hidden");

}


/* =========================================
   HOME
========================================= */

function goHome() {

    window.location.href =
        "index.html";

}