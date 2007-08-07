from django.template import loader, Context
from django.utils.datastructures import MultiValueDict

BOX_INFO = 'ella.core.box.BOX_INFO'
MEDIA_KEY = 'ella.core.box.MEDIA_KEY'
class Box(object):
    """
    Base Class that handles the boxing mechanism.
    """
    js = []
    css = []
    def __init__(self, obj, box_type, nodelist, template_name=None):
        self.obj = obj
        self.box_type = box_type
        self.nodelist = nodelist
        self.template_name = template_name

    def parse_params(self, definition):
        """
        A helper function to parse the parameters inside the box tag
        """
        for line in definition.split('\n'):
            pair = line.split(':', 1)
            if len(pair) == 2:
                yield (pair[0].strip(), pair[1].strip())
            else:
                pass
                # TODO log warning

    def resolve_params(self, context):
        """
        Parse the parameters into a dict.
        """
        params = MultiValueDict()
        for key, value in self.parse_params(self.nodelist.render(context)):
            params.appendlist(key, value)
        return params

    def prepare(self, context):
        """
        Do the pre-processing - render and parse the parameters and
        store them for further use in self.params.
        """
        context.push()
        context['object'] = self.obj
        self.params = self.resolve_params(context)
        context.pop()
        self._context = context

        # TODO add caching
        #self.render = cache_function(self.render, self.get_key())

    def get_context(self):
        """
        Get context to render the template.
        """
        level = self.params.get('level', 1)
        return {'object' : self.obj, 'level' : level, 'next_level' : level + 1}

    #@cache_function
    def render(self):
        """
        The main function that takes care of the rendering.
        """
        if self.template_name:
            return loader.render_to_string(self.template_name, self.get_context())

        t_list = []
        base_path = 'box/%s.%s/' % (self.obj._meta.app_label, self.obj._meta.module_name)
        if hasattr(self.obj, 'slug'):
            t_list.append(base_path + '%s/%s.html' % (self.box_type, self.obj.slug))
        t_list.append(base_path + '%s.html' % (self.box_type,))
        t_list.append(base_path + 'base_box.html')

        media = self._context.dicts[-1].setdefault(MEDIA_KEY, {'js' : set([]), 'css' : set([])})
        my_media = self.get_media()
        media['js'] = media['js'].union(my_media['js'])
        media['css'] = media['css'].union(my_media['css'])

        return loader.render_to_string(t_list, self.get_context())

    def get_media(self):
        """
        Get a list of media files requested by the tag.
        """
        if u'js' in self.params:
            js = set(self.js + self.params.getlist('js'))
        else:
            js = set(self.js)

        if u'css' in self.params:
            css = set(self.css + self.params.getlist('css'))
        else:
            css = set(self.css)

        return {'js' : js, 'css' : css,}

    def get_cache_key(self):
        return 'ella.core.box.Box.render:%s:%s:%s:%s' % (
                self.obj.__class__.__name__,
                self.box_type,
                self.obj._get_pk_val(),
                ','.join('%s:%s' % (key, self.params[key]) for key in sorted(self.params.keys()))
)
