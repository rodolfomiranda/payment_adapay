/**
 * 
 *  Create alert info element
 */
const createAlertInfoMessage = () => {
    const divParentNode = document.getElementById("payment-address--title");
    let divAlert = document.getElementById("alert-copied");
    console.log("veamos", divAlert)
    if (!divAlert) {
        divAlert = document.createElement("div");
        divAlert.className = "alert-copied";
        divAlert.textContent = "Copied!";
        divAlert.id = "alert-copied";
        console.log("creado", divAlert)
    }
    divAlert.style.display = 'block';
    setTimeout(() => {
        divAlert.style.display = 'none';
    }, 1000);
    return divParentNode.insertBefore(divAlert, null);
};

/**
 *
 * Copy to the clipboard the value of the Adapay address
 */
const copyToClipboard = () => {
    const adapayAddressValue = document.getElementById("adapay-address-value");

    if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(adapayAddressValue.value);

        return createAlertInfoMessage();
    }
    // If older browser
    return Promise.reject("The Clipboard API is not available.");
};