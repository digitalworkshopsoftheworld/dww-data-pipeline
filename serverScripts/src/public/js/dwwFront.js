var mapFileData;
var reverseMapData;
var mapQueryData;
var bUsemapFileData = true;

var capitalize = function(str) {
    return str.replace(/(?:^|\s)\S/g, function(a) {
        return a.toUpperCase();
    });
};

var dwwFront = {
    GetMappingListTable: function() {
        $.ajax({
            url: mapListUrl,
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            success: dwwFront.BuildMappingTable,
            error: function(xhr, status) {
                console.log("HTTP problem!");
            }
        });
    },

    GetMapFile: function() {
        $.ajax({
            url: mapFileUrl,
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            success: function(json) {
                mapFileData = json;
                reverseMapData = dwwFront.BuildReverseMap(mapFileData);
                console.log(reverseMapData);
                dwwFront.GetMappingListTable();
            },
            error: function(xhr, status) {
                console.log("HTTP problem!");
            }
        });
    },

    BuildReverseMap: function(mapFile) {
        //Get entries that match the map first to build up ui controls
        reverseMapFile = {}
        $.each(mapFile, function(d) {
            //Build reverse list
            if (this.name in reverseMapFile) {
                reverseMapFile[this.name].searches.push(d);
            } else {
                reverseMapFile[this.name] = {
                    "id": this.id,
                    "searches": [d]
                }
            }
        });

        return reverseMapFile;
    },

    BuildMappingTable: function(json) {
        mapQueryData = json;
        $('#datatable tbody').html("");

        //Build table
        $.each(json, function() {
            var rowStr = "<tr><td class='searchHeader'>" + this.search + "</td>";
            rowStr += "<td class='nameHeader'>" + this.name + "</td>";
            rowStr += "<td class='searchCountHeader'>" + this.searchcount + "</td>";
            rowStr += "<td class='verifyControls'><div class='verifySection'></div><button class='verifyButton'></button></td></tr>";
            var table = $('#datatable tbody');
            var row = $(rowStr).appendTo(table);
            var editButton = $(row).find(".verifyControls button").button({
                text: false,
                icons: {
                    primary: "ui-icon-pencil"
                }
            }).click(dwwFront.MapControls);

            if (bUsemapFileData) {
                if (this.search in mapFileData) {
                    $(row).addClass('verified');
                    $(row).find(".nameHeader").html(mapFileData[this.search].name);

                    //Tag rows if they require special formatting based on identifiers (role/bad data etc)
                    if (mapFileData[this.search].name.search("role:") > -1) {
                        $(row).addClass('role');
                    }
                    if (mapFileData[this.search].name.search("baddata:") > -1) {
                        $(row).addClass('baddata');
                    }
                } else {
                    $(row).addClass("unverified");
                }
            } else {
                $(row).addClass("unverified");
            }
        });
    },

    MapControls: function() {
        var editButton = $(this);
        if ($(this).hasClass("open")) {

            var newMapName = $("#newMapName").val();
            var newMapId = $("#newMapId").val();
            var searchHeader = $(this).parent().parent().find(".searchHeader").text();
            var dropdownOption = $(this).parent().find(".verifySection select :selected");

            //Link search to existing company
            if (newMapName || newMapId) {
                if (newMapName) {
                    var id = -1;
                    if (newMapId) {
                        id = newMapId;
                    }
                    mapFileData[searchHeader] = {
                        "name": newMapName,
                        "id": id
                    }
                    $(this).parent().parent().removeClass("unverified").addClass("verified");
                    dwwFront.BuildMappingTable(mapQueryData);
                    reverseMapData = dwwFront.BuildReverseMap(mapFileData);
                } else {
                    $.pnotify({
                        title: 'Mapping error',
                        text: 'Need to provide a name!',
                        animate_speed: 'fast'
                    });
                }
            }

            $(editButton).show();

            //Cleanup
            //$(this).html("Verify");
            $(this).parent().find(".verifySection").html("");
            $(this).removeClass("open");
        } else {
            //Clear existing open dialogs
            $(this).hide();
            $(".verifySection").html("");
            $(this).addClass("open");
            dwwFront.BuildMapDropdown($(this).parent().find(".verifySection"));
            $("<input id='newMapName' type='text' placeholder='" + capitalize(mapType) + " name'>").appendTo($(this).parent().find(".verifySection"));
            if (mapType != "role") {
                $("<input id='newMapId' type='text' placeholder='" + capitalize(mapType) + " ID'>").appendTo($(this).parent().find(".verifySection"));
            }
            $("<button id='saveFieldButton'>Save</button>").button().click(function() {
                $(editButton).click();
            }).appendTo($(this).parent().find(".verifySection"));
        }
    },

    BuildMapDropdown: function(parent) {
        var dropdown = $("<select>").appendTo($(parent)).change(function() {
            var name = $("select :selected").html();
            var id = $("select :selected").val()
            if ($("select :selected").html() == "-Role-") {
                name = "role:" + $(this).parent().parent().parent().find(".searchHeader").text();
                id = "-1";
            } else if ($("select :selected").html() == "-Bad Data-") {
                name = "baddata:" + $(this).parent().parent().parent().find(".searchHeader").text();
                id = "-1";
            } else if ($("select :selected").html() == "--New " + capitalize(mapType) + "--") {
                name = ""
                id = ""
            }

            $(parent).find("#newMapName").val(name);
            $(parent).find("#newMapId").val(id);
        });

        $("<option>").attr("value", this.id).html("--New " + capitalize(mapType) + "--").appendTo(dropdown);
        $("<option>").attr("value", this.id).html("-Bad Data-").appendTo(dropdown);
        if (mapType == "company") {
            $("<option>").attr("value", this.id).html("-Role-").appendTo(dropdown);
        }

        $.each(reverseMapData, function(key, val) {
            if (key.search("role:") < 0 && (key.search("baddata:") < 0)) {
                $("<option>").attr("value", this.id).html(key).appendTo(dropdown);
            }
        });

        //Sort alphabetically
        var listitems = dropdown.children('option').get();
        listitems.sort(function(a, b) {
            return $(a).text().toUpperCase().localeCompare($(b).text().toUpperCase());
        })
        $.each(listitems, function(idx, itm) {
            dropdown.append(itm);
        });
    }
};


$(document).ready(function() {
    dwwFront.GetMapFile();

    $("#useMapButton").button().click(function() {
        bUsemapFileData = !bUsemapFileData;
        dwwFront.BuildMappingTable(mapQueryData);
    });

    $("#uploadMap").button().click(function() {
        $.ajax({
            url: document.URL,
            type: "POST",
            data: JSON.stringify(mapFileData),
            contentType: "application/json",
            success: function(data) {
                $.pnotify({
                    title: 'Finished',
                    text: 'Mappings updated.',
                    type: 'info',
                    animate_speed: 'fast'
                });
                dwwFront.BuildMappingTable(mapQueryData);
            },
            error: function(xhr, status) {
                console.log("HTTP problem!");
            }
        });
    });
});