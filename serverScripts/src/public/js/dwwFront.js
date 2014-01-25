var mapFileData;
var reverseMapData;
var mapQueryData;
var bUsemapFileData = true;
var minSearchFilter = 1;
var openDialog;

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
                    "searches": [d],
                    "total": 0
                }
            }
        });

        $("#datatable .verified").each(function(d) {
            reverseMapFile[$(this).find(".nameHeader").text()].total += parseInt($(this).find(".searchCountHeader").text());
        });

        return reverseMapFile;
    },

    BuildMappingTable: function(json) {
        mapQueryData = json;
        $('#datatable tbody').html("");

        //Build table
        $.each(json, dwwFront.BuildRow);

        //Build totals table
        reverseMapData = dwwFront.BuildReverseMap(mapFileData);
        dwwFront.BuildTotalsTable();
        $(document.body).trigger("sticky_kit:recalc")

        console.log(reverseMapData);
    },

    BuildRow: function() {
        if (this.searchcount < minSearchFilter) {
            return;
        }

        var table = $('#datatable tbody');
        var row = $("<tr>").attr("id", "s_" + this.orderid).appendTo(table);
        var searchHeaderTd = $("<td>").addClass('searchHeader').text(this.search).appendTo(row);
        var nameHeaderTd = $("<td>").addClass('nameHeader').text(this.name).appendTo(row);
        var searchCountTd = $("<td>").addClass('searchCountHeader').text(this.searchcount).appendTo(row);
        var verifyControls = $("<td>").addClass('verifyControls').appendTo(row);
        var verifySection = $("<div>").addClass('verifySection').appendTo(verifyControls);
        var verifyButton = $("<button>").addClass('verifyButton').click(dwwFront.MapControls).appendTo(verifyControls);

        dwwFront.UpdateRow(this);
    },

    UpdateRow: function(key, data) {
        if (!data) {
            data = key;
        }

        var nameHeaderTd = $("#s_" + data.orderid + " .nameHeader");
        var row = nameHeaderTd.parent();

        if (bUsemapFileData) {
            if (data.search in mapFileData) {
                row.addClass('verified');
                nameHeaderTd.html(mapFileData[data.search].name);

                //Tag rows if they require special formatting based on identifiers (role/bad data etc)
                if (mapFileData[data.search].name.search("role:") > -1) {
                    row.addClass('role');
                }
                if (mapFileData[data.search].name.search("baddata:") > -1) {
                    row.addClass('baddata');
                }
            } else {
                row.addClass("unverified");
            }
        } else {
            row.addClass("unverified");
        }
    },

    BuildTotalsTable: function() {
        $("#sidebar tbody").html("");
        $.each(reverseMapData, function(key, value) {
            if (value.total < minSearchFilter) {
                return;
            }
            var row = $("<tr>").addClass("verified").appendTo($("#sidebar tbody"));
            var mappedNameTd = $("<td>").addClass("mappedNameHeader").html(key).appendTo(row);
            var countTotalTd = $("<td>").addClass("countTotalHeader").html(value.total).appendTo(row);
        });
    },

    MapControls: function() {
        var target = $(this);
        var verifySection = target.parent().find("div.verifySection");

        //Close editor dialog and update table
        if (target.hasClass("open")) {

            var newMapName = $("#newMapName").val();
            var newMapId = $("#newMapId").val();
            var searchHeader = target.parent().parent().find("td.searchHeader").text();
            var dropdownOption = target.parent().find("div.verifySection select :selected");

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
                    $(target).parent().parent().removeClass("unverified").addClass("verified");

                    //Update table values
                    $.each(mapQueryData, dwwFront.UpdateRow);
                    reverseMapData = dwwFront.BuildReverseMap(mapFileData);
                    dwwFront.BuildTotalsTable();
                }
            }

            //Cleanup
            target.removeClass("open").show();
            verifySection.html("");
            openDialog = null;
            //$(document.body).trigger("sticky_kit:recalc")

        } else {
            //Clear existing open dialogs
            target.addClass("open").hide();
            if (openDialog) {
                $(openDialog).find("button").removeClass("open").show();
                $(openDialog).find("div.verifySection").html("");
            }

            openDialog = target.parent();

            dwwFront.BuildMapDropdown(verifySection);
            $("<input id='newMapName' type='text' placeholder='" + capitalize(mapType) + " name'>").appendTo(verifySection);
            if (mapType != "role") {
                $("<input id='newMapId' type='text' placeholder='" + capitalize(mapType) + " ID'>").appendTo(verifySection);
            }
            $("<button id='saveFieldButton'>Save</button>").click(function() {
                target.click();
            }).appendTo(verifySection);
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

    //$("#sidebar").stick_in_parent();
    $("#maintable").stupidtable().bind('aftertablesort', function(event, data) {
        $("#maintable button").click(dwwFront.MapControls);
    });
    $("#totalstable").stupidtable();

    $("#useMapButton").click(function() {
        bUsemapFileData = !bUsemapFileData;
        dwwFront.BuildMappingTable(mapQueryData);
    });

    $("#uploadMap").click(function() {
        $.ajax({
            url: document.URL,
            type: "POST",
            data: JSON.stringify(mapFileData),
            contentType: "application/json",
            success: function(data) {
                alert("Upload complete");
                //dwwFront.BuildMappingTable(mapQueryData);
            },
            error: function(xhr, status) {
                console.log("HTTP problem!");
            }
        });
    });

    $("#searchCutoff").change(function() {
        minSearchFilter = $(this).val();
        dwwFront.BuildMappingTable(mapQueryData);
    });
});