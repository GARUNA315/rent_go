function searchVehicle() {

    const type = document.getElementById("vehicleType").value;
    const location = document.getElementById("location").value;

    if (type === "" && location === "") {
        alert("Please select vehicle type or enter location.");
        return;
    }

    // Later this will call your Django API
    console.log("Vehicle Type:", type);
    console.log("Location:", location);

    window.location.href =
        "vehicles.html?type=" +
        encodeURIComponent(type) +
        "&location=" +
        encodeURIComponent(location);
}