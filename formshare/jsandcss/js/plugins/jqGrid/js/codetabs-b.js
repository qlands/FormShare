function codeTabs(tabData) {

    $("#codetabs").css({"height": "450px","width": "780px","margin-left" :"18px","-webkit-tab-size": 4,
"-moz-tab-size": 4,
"-ms-tab-size": 4,
"-o-tab-size": 4,
"tab-size": 4});

    var ul = $("<ul class='nav nav-tabs' role='tablist'>");
    var span = $("#codetabs");
    var divs = [];

    for (var i = 0; i < tabData.length; i++) {
        var anchor = $("<a role='tab' data-toggle='tab'>")
            .attr("href", "#codetabs-" + i)
			.attr("aria-controls", "codetabs-" + i)
            .html(tabData[i].name);
        var li = $("<li role='presentation'>");
		if(i===0) {
			li.addClass('active');
		}
		li.append(anchor);

        ul.append(li);

        var div;
        if (tabData[i].name === "Description") {
            div = $("<div role='tabpanel' class='tab-pane' style='height:350px; width:780px; overflow-y:scroll; font-size: 150%;'>");
        } else {
            div = $("<div role='tabpanel' class='tab-pane' style='height:350px; width:780px; overflow-y:scroll; font-size: 135%;'>");
        }
		if(i===0) {
			div.addClass('active');
		}
        div.attr("id", "codetabs-" + i);
                    
        divs.push(div);
    }

    //var anchor = $("<a>").attr("href", "#codetabs-" + tabData.length).attr("aria-controls", "codetabs-" + i)
                        // .html("Theme");
    //var li = $("<li>").append(anchor);

   //ul.append(li);

    //var div = $("<div role='tabpanel' class='tab-pane'>").attr("id", "codetabs-" + tabData.length);

    //divs.push(div);

    span.append(ul).append('<div class="tab-content"></div>');
	//span.tab();
$('#codetabs a').click(function (e) {
  e.preventDefault();
  $(this).tab('show');
});
    for (var i = 0; i < divs.length; i++) {
        $(".tab-content").append(divs[i]);
    }

    //span.tab();

    for (var i = 0; i < tabData.length; i++) {
        var url = tabData[i].url;
        var divID = "codetabs-" + i;
        getFileText(url, divID, tabData[i].name);
    }


    $("<span><br/>Switch theme:<br/><span><div id='switcher'></div>").appendTo("#codetabs-" + tabData.length);
    addThemeTab();
};

function outerHTML(elem) {
    return $('<div>').append(elem.clone()).html();
};

function getFileText(url, divID, /*lang*/ tabName) {
    $.ajax({
        url: url,
        dataType: "text",
        success: function (data) {
            var preTag;
            if (tabName !== "Description") {
                preTag = $("<pre>").addClass("prettyprint");
            } else {
                preTag = $("<span>");
            }           

            var strippedData = removeCodeTabsCode(data);
            tabName === "Description" ? preTag.html(strippedData) : preTag.text(strippedData);            
            $("#" + divID).append(preTag);
           
            if (tabName !== "Description") {
                prettyPrint();
            }
        }
    });
};

function removeCodeTabsCode(html) {
    var beginBlock = "<!-- This code is related to code tabs -->";
    var endBlock = " <!-- End of code related to code tabs -->";
    var beginIndex = html.indexOf(beginBlock);
    var endIndex = html.indexOf(endBlock);

    if (beginIndex > -1) {
        var blockToRemove = html.substr(beginIndex, endIndex - beginIndex + endBlock.length);
        var result = html.replace(blockToRemove, "");
        
        return result;
    }

    return html;
}

function addThemeTab() {
    var switcher = $('#switcher');
    if (switcher.length) {
        //switcher.themeswitcher();
    }
    else {
        //console.log("no switcher");
    }
};

var themeChooserText = "Switch theme: <div id='switcher'></div>";
