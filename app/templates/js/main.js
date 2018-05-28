;(function () {
  $('.format-date').html(function(i, value) {
    return moment(value).fromNow()
  }).addClass('show')
  
  $(function() {
    $('.rating').barrating({
      theme: 'bootstrap-stars',
      deselectable: false,
      showSelectedRating: false,
    })

    $('.rating-readonly').each(function () {
      $(this).barrating({
        theme: 'bootstrap-stars',
        showSelectedRating: false,
        readonly: true,
        initialRating: $(this).attr('v')
      })
    })
    
    $('.score-tag').addClass('show')
  })
  
  $('.avatar-input').on('change', function (ev) {
    if (ev.target.files && ev.target.files[0]) {
      var reader = new FileReader()

      reader.onload = function(e) {
        $('.avatar-preview').attr('src', e.target.result)
      }

      reader.readAsDataURL(ev.target.files[0])
    }
  })

  // polling per 5s
  var interval = 5000

  var notificationElement = $('.notification')
  var notificationCntElement = $('.notification-val')

  function updateNotification() {
    $.get('/inbox/unread', function (cnt) {
      console.log(notificationElement)

      if (cnt > 0) {
        notificationElement.addClass('show')
        notificationCntElement.text(cnt)
      } else {
        notificationElement.removeClass('show')
      }

      setTimeout(updateNotification, interval)
    })
  }

  updateNotification()
})();
