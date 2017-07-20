# ------------------------------------------------------------------------------
# This file is part of Appy, a framework for building applications in the Python
# language. Copyright (C) 2007 Gaetan Delannay

# Appy is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.

# Appy is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# Appy. If not, see <http://www.gnu.org/licenses/>.

# ------------------------------------------------------------------------------
from appy.px import Px
from appy.gen import utils as gutils
from appy.gen.indexer import defaultIndexes
from appy.shared import utils as sutils
from group import Group

# ------------------------------------------------------------------------------
class Search:
    '''Used for specifying a search for a given class.'''
    def __init__(self, name, group=None, sortBy='', sortOrder='asc', limit=None,
                 default=False, colspan=1, translated=None, show=True,
                 translatedDescr=None, **fields):
        self.name = name
        # Searches may be visually grouped in the portlet.
        self.group = Group.get(group)
        self.sortBy = sortBy
        self.sortOrder = sortOrder
        self.limit = limit
        # If this search is the default one, it will be triggered by clicking
        # on main link.
        self.default = default
        self.colspan = colspan
        # If a translated name or description is already given here, we will
        # use it instead of trying to translate from labels.
        self.translated = translated
        self.translatedDescr = translatedDescr
        # Condition for showing or not this search
        self.show = show
        # In the dict below, keys are indexed field names or names of standard
        # indexes, and values are search values.
        self.fields = fields

    @staticmethod
    def getIndexName(fieldName, usage='search'):
        '''Gets the name of the technical index that corresponds to field named
           p_fieldName. Indexes can be used for searching (p_usage="search") or
           for sorting (usage="sort"). The method returns None if the field
           named p_fieldName can't be used for p_usage.'''
        if fieldName == 'title':
            if usage == 'search':  return 'Title'
            else:                  return 'SortableTitle'
            # Indeed, for field 'title', Appy has a specific index
            # 'SortableTitle', because index 'Title' is a TextIndex
            # (for searchability) and can't be used for sorting.
        elif fieldName == 'state': return 'State'
        elif fieldName == 'created': return 'Created'
        elif fieldName == 'modified': return 'Modified'
        elif fieldName in defaultIndexes: return fieldName
        else:
            return 'get%s%s'% (fieldName[0].upper(),fieldName[1:])

    @staticmethod
    def getSearchValue(fieldName, fieldValue, klass):
        '''Returns a transformed p_fieldValue for producing a valid search
           value as required for searching in the index corresponding to
           p_fieldName.'''
        field = getattr(klass, fieldName, None)
        if (field and (field.getIndexType() == 'TextIndex')) or \
           (fieldName == 'SearchableText'):
            # For TextIndex indexes. We must split p_fieldValue into keywords.
            res = gutils.Keywords(fieldValue).get()
        elif isinstance(fieldValue, basestring) and fieldValue.endswith('*'):
            v = fieldValue[:-1]
            # Warning: 'z' is higher than 'Z'!
            res = {'query':(v,v+'z'), 'range':'min:max'}
        elif type(fieldValue) in sutils.sequenceTypes:
            if fieldValue and isinstance(fieldValue[0], basestring):
                # We have a list of string values (ie: we need to
                # search v1 or v2 or...)
                res = fieldValue
            else:
                # We have a range of (int, float, DateTime...) values
                minv, maxv = fieldValue
                rangev = 'minmax'
                queryv = fieldValue
                if minv == None:
                    rangev = 'max'
                    queryv = maxv
                elif maxv == None:
                    rangev = 'min'
                    queryv = minv
                res = {'query':queryv, 'range':rangev}
        else:
            res = fieldValue
        return res

    def updateSearchCriteria(self, criteria, klass, advanced=False):
        '''This method updates dict p_criteria with all the search criteria
           corresponding to this Search instance. If p_advanced is True,
           p_criteria correspond to an advanced search, to be stored in the
           session: in this case we need to keep the Appy names for parameters
           sortBy and sortOrder (and not "resolve" them to Zope's sort_on and
           sort_order).'''
        # Put search criteria in p_criteria
        for fieldName, fieldValue in self.fields.iteritems():
            # Management of searches restricted to objects linked through a
            # Ref field: not implemented yet.
            if fieldName == '_ref': continue
            # Make the correspondence between the name of the field and the
            # name of the corresponding index, excepted if advanced is True: in
            # that case, the correspondence will be done later.
            if not advanced:
                attrName = Search.getIndexName(fieldName)
                # Express the field value in the way needed by the index
                criteria[attrName] = Search.getSearchValue(fieldName,
                                                           fieldValue, klass)
            else:
                criteria[fieldName]= fieldValue
        # Add a sort order if specified
        if self.sortBy:
            if not advanced:
                criteria['sort_on'] = Search.getIndexName(self.sortBy,
                                                          usage='sort')
                if self.sortOrder == 'desc': criteria['sort_order'] = 'reverse'
                else:                        criteria['sort_order'] = None
            else:
                criteria['sortBy'] = self.sortBy
                criteria['sortOrder'] = self.sortOrder

    def isShowable(self, klass, tool):
        '''Is this Search instance (defined in p_klass) showable?'''
        if self.show.__class__.__name__ == 'staticmethod':
            return gutils.callMethod(tool, self.show, klass=klass)
        return self.show

class UiSearch:
    '''Instances of this class are generated on-the-fly for manipulating a
       Search from the User Interface.'''
    # PX for rendering a search.
    pxView = Px('''
     <div class="portletSearch">
      <a href=":'%s?className=%s&amp;search=%s' % \
                 (queryUrl, className, search.name)"
         class=":(search.name == currentSearch) and 'current' or ''"
         title=":search.translatedDescr">:search.translated</a>
     </div>''')

    def __init__(self, search, className, tool):
        self.search = search
        self.name = search.name
        self.type = 'search'
        self.colspan = search.colspan
        if search.translated:
            self.translated = search.translated
            self.translatedDescr = search.translatedDescr
        else:
            # The label may be specific in some special cases.
            labelDescr = ''
            if search.name == 'allSearch':
                label = '%s_plural' % className
            elif search.name == 'customSearch':
                label = 'search_results'
            else:
                label = '%s_search_%s' % (className, search.name)
                labelDescr = label + '_descr'
            self.translated = tool.translate(label)
            if labelDescr:
                self.translatedDescr = tool.translate(labelDescr)
            else:
                self.translatedDescr = ''
# ------------------------------------------------------------------------------
