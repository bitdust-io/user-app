from kivy.properties import StringProperty  # @UnresolvedImport

#------------------------------------------------------------------------------

from components import screen
from components import list_view

from lib import api_client
from lib import websock

#------------------------------------------------------------------------------

_Debug = False

#------------------------------------------------------------------------------

class SelectFriendRecord(list_view.SelectableHorizontalRecord):

    def __init__(self, **kwargs):
        super(SelectFriendRecord, self).__init__(**kwargs)
        self.visible_buttons = []


class SelectFriendListView(list_view.SelectableRecycleView):

    def on_selection_applied(self, item, index, is_selected, prev_selected):
        if _Debug:
            print('on_selection_applied', item.global_id, self.selected_item)
        if self.selected_item:
            if self.parent.parent.parent.parent.parent.result_callback:
                self.parent.parent.parent.parent.parent.result_callback(item.global_id)

#------------------------------------------------------------------------------

class SelectFriendScreen(screen.AppScreen):

    screen_header = StringProperty('Select user')

    def init_kwargs(self, **kw):
        self.result_callback = kw.pop('result_callback', None)
        self.screen_header = kw.pop('screen_header', 'Select user')
        return kw

    def get_title(self):
        return 'select user'

    def get_icon(self):
        return 'target-account'

    def populate(self, *args, **kwargs):
        api_client.friends_list(cb=self.on_friends_list_result)

    def on_pre_enter(self, *args):
        self.populate()

    def on_friends_list_result(self, resp):
        if not isinstance(resp, dict):
            self.ids.friends_list_view.data = []
            return
        result = websock.response_result(resp)
        if not result:
            self.ids.friends_list_view.data = []
            return
        self.ids.friends_list_view.data = []
        for one_friend in result:
            self.ids.friends_list_view.data.append(one_friend)

    def on_search_people_button_clicked(self, *args):
        self.main_win().select_screen(
            screen_id='search_people_screen',
            return_screen_id='select_friend_screen',
        )

#------------------------------------------------------------------------------

from kivy.lang.builder import Builder 
Builder.load_file('./screens/screen_select_friend.kv')
