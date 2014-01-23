var mapFileData;
var companyQueryData;
var bUsemapFileData = true;

var dwwFront = {
    GetCompanyTable: function() {
        $.ajax({
            url: mapListUrl,
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            success: dwwFront.BuildCompanyTable,
            error: function(xhr, status) {
                console.log("HTTP problem!");
            }
        });
    },

    BuildCompanyTable: function(json) {
        companyQueryData = json;
        $('#datatable').html("");
        $('#datatable').append("<table />");
        $('#datatable table').append("<thead />").append("<tbody />");
        $('#datatable thead')
            .append("<td>Search</td>")
            .append("<td>Company</td>")
            .append("<td>Search count</td>")
            .append("<td></td>");

        //Build table
        $.each(json, function() {
            var table = $('#datatable tbody');
            var row = $("<tr><td class='companySearch'>" + this.search + "</td><td class='companyName'>" + this.company + "</td><td>" + this.searchcount + "</td></tr>").appendTo(table);
            var cell = $("<td class='verifyControls'>").appendTo(row);
            $("<div>").addClass("verifySection").appendTo(cell);
            $("<button>").addClass("verifyButton").appendTo(cell).html("Verify").click(dwwFront.MapControls);

            if (bUsemapFileData) {
                if (this.search in mapFileData) {
                    $(row).addClass('verified');
                    $(row).find(".companyName").html(mapFileData[this.search].company);

                    //Tag rows if they require special formatting based on identifiers (role/bad data etc)
                    if (mapFileData[this.search].company.search("role:") > -1) {
                        $(row).addClass('role');
                    }
                    if (mapFileData[this.search].company.search("baddata:") > -1) {
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
        if ($(this).hasClass("open")) {

            var newCompanyName = $("#newCompanyName").val();
            var newCompanyId = $("#newCompanyId").val();
            var companySearch = $(this).parent().parent().find(".companySearch").text();
            var dropdownOption = $(this).parent().find(".verifySection select :selected");

            //Link search to existing company
            if (newCompanyName || newCompanyId) {
                if (newCompanyName) {
                    var id = -1;
                    if (newCompanyId) {
                        id = newCompanyId;
                    }

                    mapFileData[companySearch] = {
                        company: newCompanyName,
                        id: id
                    }
                    $(this).parent().parent().removeClass("unverified").addClass("verified");
                    //$(this).parent().parent().find(".verifyControls");
                } else {
                    $.pnotify({
                        title: 'Mapping error',
                        text: 'Need to provide a name!',
                        animate_speed: 'fast'
                    });
                }
            }

            dwwFront.BuildCompanyTable(companyQueryData);

            console.log(mapFileData);

            //Cleanup
            $(this).html("Verify");
            $(this).parent().find(".verifySection").html("");
            $(this).removeClass("open");
        } else {
            //Clear existing open dialongs
            $(".verifySection").html("");
            $(".verifyButton").html("Verify");
            $(this).html("Save");
            $(this).addClass("open");
            dwwFront.BuildCompanyDropdown($(this).parent().find(".verifySection"));
            var newCompanyName = $("<input id='newCompanyName' type='text' placeholder='Company Name'>").appendTo($(this).parent().find(".verifySection"));
            var newCompanyId = $("<input id='newCompanyId' type='text' placeholder='Company ID'>").appendTo($(this).parent().find(".verifySection"));
        }
    },

    BuildCompanyDropdown: function(parent) {
        var dropdown = $("<select>").appendTo($(parent)).change(function() {
            var name = $("select :selected").html();
            var id = $("select :selected").val()
            if ($("select :selected").html() == "-Role-") {
                name = "role:" + $(this).parent().parent().parent().find(".companySearch").text();
                id = "-1";
            } else if ($("select :selected").html() == "-Bad Data-") {
                name = "baddata:" + $(this).parent().parent().parent().find(".companySearch").text();
                id = "-1";
            } else if ($("select :selected").html() == "--New Company--") {
                name = ""
                id = ""
            }

            $(parent).find("#newCompanyName").val(name);
            $(parent).find("#newCompanyId").val(id);
        });

        $("<option>").attr("value", this.id).html("--New Company--").appendTo(dropdown);
        $("<option>").attr("value", this.id).html("-Role-").appendTo(dropdown);
        $("<option>").attr("value", this.id).html("-Bad Data-").appendTo(dropdown);

        $.each(mapFileData, function() {
            if (this.company.search("role:") < 0 && (this.company.search("baddata:") < 0)) {
                $("<option>").attr("value", this.id).html(this.company).appendTo(dropdown);
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
    },

    GetCompanyMap: function() {
        $.ajax({
            url: mapFileUrl,
            type: "GET",
            dataType: "json",
            contentType: "application/json",
            success: function(json) {
                // //Get entries that match the map first to build up ui controls
                // reversemapFileData = {}
                // $.each(json, function(d) {
                //     //Build reverse list
                //     if (this.company in reversemapFileData) {
                //         reversemapFileData[this.company].searches.push(d);
                //     } else {
                //         reversemapFileData[this.company] = {
                //             id: this.id,
                //             searches: [d]
                //         }
                //     }
                // });
                mapFileData = json;
                dwwFront.GetCompanyTable();
            },
            error: function(xhr, status) {
                console.log("HTTP problem!");
            }
        });
    }
};


$(document).ready(function() {
    dwwFront.GetCompanyMap();

    $("#useMapButton").click(function() {
        bUsemapFileData = !bUsemapFileData;
        dwwFront.BuildCompanyTable(companyQueryData);
    });

    $("#uploadMap").click(function() {
        $.ajax({
            url: document.URL,
            type: "POST",
            data: JSON.stringify(mapFileData),
            contentType: "application/json",
            success: function(data) {
                $.pnotify({
                    title: 'Info',
                    text: 'Mappings updated.',
                    type: 'info',
                    animate_speed: 'fast'
                });
                dwwFront.BuildCompanyTable(companyQueryData);
            },
            error: function(xhr, status) {
                console.log("HTTP problem!");
            }
        });
    });
});