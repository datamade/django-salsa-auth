function getFormData(form){
    var form_array = form.serializeArray();
    var form_obj = {};
    $.map(form_array, function(n, i){
        form_obj[n['name']] = n['value'];
    });
    return form_obj;
};

function submitForm(url, form_data){
    $.post(url, form_data, function(response){
        if (response['redirect_url']){
            window.location = response['redirect_url'];
        }
        $.each(response.errors, function(field, value){
            var selector = '#' + field + '-errors';
            $(selector).html(value[0]);
        })
    });
};

$(document).on('click', '.toggle-login-signup', function(e){
    var parent_modal = $(e.target).data('parent_modal');
    if (parent_modal == 'loginModal'){
        $('#loginModal').modal('hide');
        $('#signupModal').modal();
    } else {
        $('#signupModal').modal('hide');
        $('#loginModal').modal();
    }
});

$('#login-form').submit(function(e) {
    e.preventDefault();
    var form_data = getFormData($('#login-form'));
    submitForm('/mailchimp/login/', form_data);
});
