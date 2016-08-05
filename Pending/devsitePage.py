import os
import re
import yaml
import logging
import markdown
import devsiteHelper
from google.appengine.ext.webapp.template import render

SOURCE_PATH = os.path.join(os.path.dirname(__file__), 'src/content/')
UNSUPPORTED_TAGS = [
  r'{% link_sample_button .+%}',
  r'{% include_code (.+)%}'
]

def getPage(requestPath, lang):
  response = None
  title = 'Web Fundamentals'
  leftNav = '- No Left Nav Found - '
  toc = '- No TOC Found - '
  fileLocations = [
    os.path.join(SOURCE_PATH, lang, requestPath) + '.md',
    os.path.join(SOURCE_PATH, 'en', requestPath) + '.md',
    os.path.join(SOURCE_PATH, lang, requestPath) + '.jshtml',
    os.path.join(SOURCE_PATH, 'en', requestPath) + '.jshtml',
  ]
  for fileLocation in fileLocations:
    if os.path.isfile(fileLocation):
      content = open(fileLocation, 'r').read()
      content = content.decode('utf8')

      # If it's a .jshtml file, just serve it.
      if fileLocation.endswith('.jshtml'):
        return content

      # Remove any comments {# something #} from the markdown
      content = re.sub(r'{#.+?#}', '', content)

      # Show warning for unsupported elements
      for tag in UNSUPPORTED_TAGS:
        if re.search(tag, content) is not None:
          logging.warn(' - Unsupported tag: ' + tag)
          replaceWith = '<aside class="warning">Web<strong>Fundamentals</strong>: '
          replaceWith += '<span>Unsupported tag: <code>' + tag + '</code></span></aside>'
          content = content.replace(tag, replaceWith)

      # Render any DevSite specific tags
      content = devsiteHelper.renderDevSiteContent(content, lang)

      # If it's a markdown file, parse it to HTML
      if fileLocation.endswith('.md'):
        content = re.sub(r'^Success: (.*?)\n{2}(?ms)', r'<aside class="success" markdown="1"><strong>Success:</strong> <span>\1</span></aside>', content)
        content = re.sub(r'^Dogfood: (.*?)\n{2}(?ms)', r'<aside class="dogfood" markdown="1"><strong>Dogfood:</strong> <span>\1</span></aside>', content)
        content = re.sub(r'^Note: (.*?)\n{2}(?ms)', r'<aside class="note" markdown="1"><strong>Note:</strong> <span>\1</span></aside>', content)
        content = re.sub(r'^Caution: (.*?)\n{2}(?ms)', r'<aside class="caution" markdown="1"><strong>Caution:</strong> <span>\1</span></aside>', content)
        content = re.sub(r'^Warning: (.*?)\n{2}(?ms)', r'<aside class="warning" markdown="1"><strong>Warning:</strong> <span>\1</span></aside>', content)

        # Adds a set of markdown extensions available to us on DevSite
        ext = [
          'markdown.extensions.attr_list', # Adds support for {: #someid }
          'markdown.extensions.meta', # Removes the meta data from the top of the doc
          'markdown.extensions.toc', # Generate the TOC for the right side
          'markdown.extensions.tables', # Support for Markdown Tables
          'markdown.extensions.extra', # Support for markdown='1' in tags
          'markdown.extensions.def_list' # Support for definition lists
        ]
        md = markdown.Markdown(extensions=ext)
        content = md.convert(content)

        # Reads the book.yaml file and generate the lefthand nav
        if 'book_path' in md.Meta and len(md.Meta['book_path']) == 1:
          bookPath = md.Meta['book_path'][0]
          leftNav = devsiteHelper.getLeftNav(requestPath, bookPath, lang)

        # Build the table of contents & transform so it fits within DevSite
        toc = md.toc
        toc = toc.strip()
        toc = re.sub(r'<div class="toc">', '', toc) # remove <div> wrapper
        toc = re.sub(r'</div>', '', toc) # remove <div> wrapper
        toc = re.sub('<ul>', '', toc, 1) # Remove outer <ul></ul>
        toc = toc[:toc.rfind('</ul>')] # Remove outer <ul></ul>
        # Add appropriate classes
        toc = re.sub(r'<ul>', '<ul class="devsite-page-nav-list">', toc)
        toc = re.sub(r'<a href', '<a class="devsite-nav-title" href', toc)
        toc = re.sub(r'<li>', '<li class="devsite-nav-item">', toc)

      # Replaces <pre> tags with prettyprint enabled tags
      content = re.sub(r'^<pre>(?m)', r'<pre class="prettyprint">', content)

      # Get the page title from the markup.
      titleRO = re.search(r'<h1 class="page-title".*?>(.*?)<\/h1>', content)
      if titleRO:
        title = titleRO.group(1)

      # Renders the content into the template
      response = render('gae/article.tpl', {
        'title': title,
        'leftNav': leftNav,
        'content': content,
        'toc': toc,
        'lang': lang}
      )
      break

  return response
