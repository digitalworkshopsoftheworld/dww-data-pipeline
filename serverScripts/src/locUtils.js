// Pulled from stack overflow - tests in Google Earth using their distance tool agree with this method 
function getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2) {
    function deg2rad(deg) {
        return deg * (Math.PI / 180);
    }
    var R = 6371; // Radius of the earth in km
    var dLat = deg2rad(lat2 - lat1);
    var dLon = deg2rad(lon2 - lon1);
    var a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    var d = R * c; // Distance in km
    return d;
}

function getMaxCount(distance) {
    //maximum distance is ~ 20,000 km => 200 days is the longest any one trip should take
    //1 day should be the minimum time a trip should take   
    return Math.floor(distance / 100) < 1 ? 1 : Math.floor(distance / 100);
}

exports.GetTripLengthDays = function(loc1, loc2) {
    split1 = loc1.split(",");
    lat1 = parseFloat(split1[0]);
    lon1 = parseFloat(split1[1]);
    split2 = loc2.split(",");
    lat2 = parseFloat(split2[0]);
    lon2 = parseFloat(split2[1]);
    time = getMaxCount(getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2));
    //console.log(loc1, lat1, lon1, loc2, lat2, lon2, time);
    return time; //specify the respective lat/lon's here!! 
}