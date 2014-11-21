assert = chai.assert
sinon.assert.expose(assert, prefix: '')

describe 'Annotator.Guest', ->
  createGuest = (options) ->
    element = document.createElement('div')
    return new Annotator.Guest(element, options || {})

  # Silence Annotator's sassy backchat
  before -> sinon.stub(console, 'log')
  after -> console.log.restore()

  describe 'onAdderMouseUp', ->
    it 'it prevents the default browser action when triggered', () ->
      event = jQuery.Event('mouseup')
      guest = createGuest()
      guest.onAdderMouseup(event)
      assert.isTrue(event.isDefaultPrevented())

    it 'it stops any further event bubbling', () ->
      event = jQuery.Event('mouseup')
      guest = createGuest()
      guest.onAdderMouseup(event)
      assert.isTrue(event.isPropagationStopped())

  describe 'Guest.annotationFormatter', ->
    it 'fills the annotation.uri field', ->
      guest = createGuest()
      annotation = {}
      expected = guest.getHref()
      formatted = guest.formatAnnotation annotation
      assert.equal formatted.uri, expected

    it 'leaves out anchors', ->
      guest = createGuest()
      annotation =
        anchors: 'Will be left out'

      formatted = guest.formatAnnotation annotation
      assert.isFalse 'anchors' of formatted

    it 'copies all other keys', ->
      guest = createGuest()
      annotation =
        randomKey: 'Will stay'
        testKey: 'This too'
        finalKey: 'Even this'

      formatted = guest.formatAnnotation annotation
      assert.equal annotation.randomKey, formatted.randomKey
      assert.equal annotation.testKey, formatted.testKey
      assert.equal annotation.finalKey, formatted.finalKey

    it 'cuts out local file-paths', ->
      guest = createGuest()
      annotation =
        document:
          link: [
            {href: 'http://test-uri.org'}
            {href: 'urn:x-pdf:c21f21ea44c1e2ed2581435fa5a2dcce'}
            {href: 'file://home/user/testuser/downloads/shiny.pdf'}
          ]

      formatted = guest.formatAnnotation annotation
      links = annotation.document.link
      formattedLinks = formatted.document.link
      assert.equal formattedLinks.length, 2
      assert.equal formattedLinks[0], links[0]
      assert.equal formattedLinks[1], links[1]

