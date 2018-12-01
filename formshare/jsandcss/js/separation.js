var updateOutput = function (e,enableButtons) {
    enableButtons = typeof enableButtons !== 'undefined' ? enableButtons : true;
    var list = e.length ? e : $(e.target),
        output = list.data('output');
    if (window.JSON) {
        output.val(window.JSON.stringify(list.nestable('serialize')));//, null, 2));
    } else {
        output.val('JSON browser support required for this demo.');
    }

    $(".clm-actions").prop('disabled', !enableButtons);
    $(".clm-grpactions").prop('disabled', enableButtons);
};

var updateOutput2 = function (e,enableButtons) {
    enableButtons = typeof enableButtons !== 'undefined' ? enableButtons : true;
    var list = e.length ? e : $(e.target),
        output = list.data('output');
    if (window.JSON) {
        output.val(window.JSON.stringify(list.nestable('serialize')));//, null, 2));
    } else {
        output.val('JSON browser support required for this demo.');
    }

    $(".clm-actions").prop('disabled', !enableButtons);
    $(".clm-grpactions").prop('disabled', enableButtons);
};

function proceed()
{
    var url = $('#urlforpost').val()
    var crfToken = $('#confirmcrftoken').val()
    var form = document.createElement('form');
    form.setAttribute('method', 'post');
    form.setAttribute('action', url);
    form.style.display = 'hidden';

    var i = document.createElement("input"); //input element, text
    i.setAttribute('type',"text");
    i.setAttribute('name',"csrf_token");
    i.setAttribute('value',crfToken)
    form.appendChild(i);

    document.body.appendChild(form)
    form.submit();
}

function ShowConfirmModal(url)
{
    $('#urlforpost').val(url)
    $('#confirm').css('width', '560px');
    $('#confirm').modal('show');
}

$('#myModal').on('hidden', function () {
    $('#confirm').css('width', 0);
});

$(document).ready(function(){

    $('#confirm').css('width', 0);
    $('#nestable').nestable({
        group: 1,
        onDragStart: function (l, e) {
            // get type of dragged element
            var type = $(e).data('type');
            // based on type of dragged element add or remove no children class
            switch (type) {
                case 'question':
                    // A question can be part of a group
                    l.find("[data-type=group]").removeClass('dd-nochildren');
                    break;
                case 'group':
                    // A group cannot be part of another group
                    l.find("[data-type=group]").addClass('dd-nochildren');
                    break;
                default:
                    console.error("Invalid type");
            }
        },
        callback: function(l,e)
        {
            $( "#nestable" ).trigger( "change" );
            $( "#nestable2" ).trigger( "change" );
        },
        beforeDragStop: function(l,e, p)
        {
            var notMoveable = $(e).data('display');
            if (notMoveable == "1")
                return false;
        }
    }).on('change', updateOutput);
    updateOutput($('#nestable').data('output', $('#nestable-output')),false);


    $('#nestable2').nestable({
        group: 1,
        onDragStart: function (l, e) {
            // get type of dragged element
            var type = $(e).data('type');
            // based on type of dragged element add or remove no children class
            switch (type) {
                case 'question':
                    // A question can be part of a group
                    l.find("[data-type=group]").removeClass('dd-nochildren');
                    break;
                case 'group':
                    // A group cannot be part of another group
                    l.find("[data-type=group]").addClass('dd-nochildren');
                    break;
                default:
                    console.error("Invalid type");
            }
        },
        callback: function(l,e)
        {
            $( "#nestable" ).trigger( "change" );
            $( "#nestable2" ).trigger( "change" );
        }
    }).on('change', updateOutput2);
    updateOutput2($('#nestable2').data('output', $('#nestable-output2')),false);

});

