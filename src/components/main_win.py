import time

#------------------------------------------------------------------------------

from kivy.clock import Clock
from kivy.properties import StringProperty  # @UnresolvedImport
from kivy.properties import NumericProperty  # @UnresolvedImport
from kivy.properties import ObjectProperty  # @UnresolvedImport
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout

from kivymd.theming import ThemableBehavior
from kivymd.uix.menu import MDDropdownMenu

#------------------------------------------------------------------------------

from lib import system

from components import webfont

#------------------------------------------------------------------------------

_Debug = False

#------------------------------------------------------------------------------

def patch_kivy_core_window():
    from kivy.core.window import Window

    def _get_android_kheight(self=Window):
        ret = system.get_android_keyboard_height()
        return ret

    def _get_size(self=Window):
        if _Debug:
            print('main_window._get_size', self)
        r = self._rotation
        w, h = self._size
        if self._density != 1:
            w, h = self._win._get_gl_size()
        if self.softinput_mode == 'resize':
            h -= system.get_android_keyboard_height()  # self.keyboard_height
        if r in (0, 180):
            return w, h
        return h, w

    def update_viewport(self=Window):
        from kivy.graphics.opengl import glViewport  # @UnresolvedImport
        from kivy.graphics.transformation import Matrix  # @UnresolvedImport
        from math import radians

        w, h = self.system_size
        if self._density != 1:
            w, h = self.size

        smode = self.softinput_mode
        target = self._system_keyboard.target
        targettop = max(0, target.to_window(0, target.y)[1]) if target else 0
        kheight = system.get_android_keyboard_height()

        w2, h2 = w / 2., h / 2.
        r = radians(self.rotation)

        x, y = 0, 0
        _h = h
        if smode == 'pan':
            y = kheight
        elif smode == 'below_target':
            y = 0 if kheight < targettop else (kheight - targettop)
        if smode == 'scale':
            _h -= kheight
        if smode == 'resize':
            y += kheight
        # prepare the viewport
        glViewport(x, y, w, _h)

        try:
            # do projection matrix
            projection_mat = Matrix()
            projection_mat.view_clip(0.0, w, 0.0, h, -1.0, 1.0, 0)
        except Exception as exc:
            if _Debug:
                print('main_window.update_viewport', exc)
            return
        self.render_context['projection_mat'] = projection_mat

        # do modelview matrix
        modelview_mat = Matrix().translate(w2, h2, 0)
        modelview_mat = modelview_mat.multiply(Matrix().rotate(r, 0, 0, 1))

        w, h = self.size
        w2, h2 = w / 2., h / 2.
        modelview_mat = modelview_mat.multiply(Matrix().translate(-w2, -h2, 0))
        self.render_context['modelview_mat'] = modelview_mat
        frag_modelview_mat = Matrix()
        frag_modelview_mat.set(flat=modelview_mat.get())
        self.render_context['frag_modelview_mat'] = frag_modelview_mat

        # redraw canvas
        self.canvas.ask_update()

        # and update childs
        self.update_childsize()

    Window.clearcolor = (1, 1, 1, 1)
    Window.fullscreen = False

    if system.is_android():
        Window.update_viewport = update_viewport
        # Window._get_size = _get_size
        Window._get_android_kheight = _get_android_kheight
        Window.keyboard_anim_args = {"d": 0.1,"t": "linear", }
        softinput_mode = 'resize'
        Window.softinput_mode = softinput_mode
        # set_android_system_ui_visibility()

    if _Debug:
        print('main_window.patch_kivy_core_window', Window)

#------------------------------------------------------------------------------

class ContentNavigationDrawer(BoxLayout):
    screen_manager = ObjectProperty()
    nav_drawer = ObjectProperty()
    main_win = ObjectProperty()

#------------------------------------------------------------------------------

class MainWin(Screen, ThemableBehavior):

    control = None
    screens_map = {}
    active_screens = {}
    dropdown_menus = {}
    screen_closed_time = {}
    selected_screen = StringProperty('')
    latest_screen = ''

    state_process_health = NumericProperty(0)
    state_identity_get = NumericProperty(0)
    state_network_connected = NumericProperty(0)

    dropdown_menu = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        patch_kivy_core_window()

    def register_screens(self, screens_dict):
        for screen_type, screen_class in screens_dict.items():
            self.screens_map[screen_type] = screen_class

    def unregister_screens(self):
        self.screens_map.clear()

    def register_controller(self, cont): 
        self.control = cont

    def unregister_controller(self): 
        self.control = None

    #------------------------------------------------------------------------------

    def is_screen_active(self, screen_id):
        return screen_id in self.active_screens

    def get_active_screen(self, screen_id):
        return self.active_screens.get(screen_id, [None, ])[0]

    def populate_toolbar_content(self, screen_inst=None):
        if not screen_inst:
            self.ids.toolbar.title = 'BitDust'
            return
        title = screen_inst.get_title()
        icn = screen_inst.get_icon()
        if icn:
            icn_pack = screen_inst.get_icon_pack()
            title = '[size=28sp]{}[/size]  {}'.format(webfont.make_icon(icn, icon_pack=icn_pack), title)
        if title:
            self.ids.toolbar.title = title
        else:
            self.ids.toolbar.title = 'BitDust'

    def populate_dropdown_menu(self, screen_id, new_items):
        if _Debug:
            print('MainWin.populate_dropdown_menu', new_items)
        # self.control.app.dropdown_menu.dismiss()
        # self.control.app.dropdown_menu.menu.ids.box.clear_widgets()
        itms = []
        for itm in new_items:
            itm.update({
                "height": "40dp",
                "top_pad": "10dp",
                "bot_pad": "10dp",
            })
            itms.append(itm)
        # self.control.app.dropdown_menu.items = itms
        # self.control.app.dropdown_menu.create_menu_items()
        self.dropdown_menus[screen_id] = MDDropdownMenu(
            caller=self.ids.dropdown_menu_placeholder,
            width_mult=3,
            items=itms,
            # selected_color=self.theme_cls.bg_darkest,
            opening_time=0,
            # radius=[0, ],
        )
        self.dropdown_menus[screen_id].bind(on_release=self.on_dropdown_menu_callback)

    def open_screen(self, screen_id, screen_type, **kwargs):
        if screen_id in self.active_screens:
            if _Debug:
                print('MainWin.open_screen   screen %r already opened' % screen_id)
            return
        screen_class = self.screens_map[screen_type]
        screen_inst = screen_class(name=screen_id, **kwargs)
        self.ids.screen_manager.add_widget(screen_inst)
        self.ids.screen_manager.current = screen_id
        self.active_screens[screen_id] = (screen_inst, None, )
        self.screen_closed_time[screen_id] = time.time()
        menu_items = screen_inst.get_dropdown_menu_items()
        if menu_items:
            self.populate_dropdown_menu(screen_id, menu_items)
        screen_inst.on_opened()
        if _Debug:
            print('MainWin.open_screen   opened screen %r' % screen_id)

    def close_screen(self, screen_id):
        if screen_id not in self.active_screens:
            if _Debug:
                print('MainWin.close_screen   screen %r has not been opened' % screen_id)
            return
        screen_inst, btn = self.active_screens.pop(screen_id)
        self.screen_closed_time.pop(screen_id, None)
        if screen_inst not in self.ids.screen_manager.children:
            if _Debug:
                print('MainWin.close_screen   WARNING   screen instance %r was not found among screen manager children')
        self.ids.screen_manager.remove_widget(screen_inst)
        screen_inst.on_closed()
        del screen_inst
        if _Debug:
            print('MainWin.close_screen  closed screen %r' % screen_id)

    def close_screens(self, screen_ids_list):
        for screen_id in screen_ids_list:
            self.close_screen(screen_id)

    def close_active_screens(self, exclude_screens=[]):
        screen_ids = list(self.active_screens.keys())
        for screen_id in screen_ids:
            if screen_id not in exclude_screens:
                self.close_screen(screen_id)

    def cleanup_screens(self, *args):
        screen_ids = list(self.active_screens.keys())
        for screen_id in screen_ids:
            if screen_id == self.selected_screen:
                continue
            closed_time = self.screen_closed_time.get(screen_id)
            if closed_time:
                if time.time() - closed_time > 5.0:
                    if _Debug:
                        print('closing inactive screen %r : %d ~ %d' % (screen_id, time.time(), closed_time, ))
                    self.close_screen(screen_id)

    def select_screen(self, screen_id, verify_state=False, screen_type=None, **kwargs):
        if screen_type is None:
            screen_type = screen_id
            if screen_type.startswith('private_chat_'):
                screen_type = 'private_chat_screen'
            if screen_type.startswith('group_'):
                screen_type = 'group_chat_screen'
        if verify_state:
            if self.state_process_health != 1 or self.state_identity_get != 1:
                if _Debug:
                    print('MainWin.select_screen   selecting screen %r not possible, state verify failed' % screen_id)
                return False
        if _Debug:
            print('MainWin.select_screen  %r' % screen_id)
        if screen_id not in self.active_screens:
            self.open_screen(screen_id, screen_type, **kwargs)
        else:
            self.active_screens[screen_id][0].init_kwargs(**kwargs)
        if self.selected_screen:
            if self.selected_screen == screen_id:
                if _Debug:
                    print('MainWin.select_screen   skip, selected screen is already %r' % screen_id)
                return True
        self.populate_toolbar_content(self.active_screens[screen_id][0])
        # self.populate_dropdown_menu([])
        if self.selected_screen:
            self.screen_closed_time[self.selected_screen] = time.time()
        if self.selected_screen not in ['process_dead_screen', 'connecting_screen', 'welcome_screen', 'startup_screen', ]:
            self.latest_screen = self.selected_screen
        self.selected_screen = screen_id
        self.ids.screen_manager.current = screen_id
        Clock.schedule_once(self.cleanup_screens)
        # self.populate_dropdown_menu(self.active_screens[screen_id][0].get_dropdown_menu_items())
        return True

    #------------------------------------------------------------------------------

    def on_right_menu_button_clicked(self, *args):
        if _Debug:
            print('MainWin.on_right_menu_button_clicked', args)
        if self.selected_screen and self.selected_screen in self.dropdown_menus:
            self.dropdown_menus[self.selected_screen].open()

    def on_dropdown_menu_callback(self, instance_menu, instance_menu_item):
        if _Debug:
            print('MainWin.on_dropdown_menu_callback', instance_menu, instance_menu_item.text)
        instance_menu.dismiss()
        if self.selected_screen:
            self.active_screens[self.selected_screen][0].on_dropdown_menu_item_clicked(
                instance_menu, instance_menu_item
            )

    def on_state_process_health(self, instance, value):
        self.control.on_state_process_health(instance, value)

    def on_state_identity_get(self, instance, value):
        self.control.on_state_identity_get(instance, value)

    def on_state_network_connected(self, instance, value):
        self.control.on_state_network_connected(instance, value)

    # def on_height(self, instance, value):
    #     if _Debug:
    #         print ('MainWin.on_height', instance, value)

    # def on_size(self, instance, value):
    #     if _Debug:
    #         print ('MainWin.on_size', instance, value)

#------------------------------------------------------------------------------

from kivy.lang.builder import Builder 
Builder.load_file('./components/main_win.kv')
