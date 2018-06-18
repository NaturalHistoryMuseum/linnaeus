$(document).ready(function() {
    var l = new Loupe(document.getElementById('thumb'));

    var changeImage = function(event) {
        var link = $(this);
        $('#thumb').attr('src', link.data().target);
        $('.nav-link').removeClass('active');
        link.addClass('active');
        l.init(document.getElementById('thumb'));
    };

    $('.nav-link').click(changeImage);
});


