#!/usr/local/bin/python3
import sys
import argparse
import importlib.util
import os
import re

# Output DNA matches in a tree view in Graphviz DOT format.
# Given a GEDCOM with people having a custom event of name as input
# and an optional note containing the cM value.
# The person for whom the matches are compared should have a note or value
# beginning with 'Me ', "Me,", "Me." or equal to "Me" (case independant).
#
# An example of a section in a gedcom file:
# 1 EVEN Ancestry
# 2 TYPE dnamatch
# 2 DATE BEF 2021
# 2 NOTE 290 cM across 15 segments
# and
# 1 EVEN
# 2 TYPE dnamatch
# 2 NOTE me
#
# Might not handle the situation where the closest shared family between
# two people doesn't exist in the data.
#
# This code is released under the MIT License: https://opensource.org/licenses/MIT
# Copyright (c) 2022 John A. Andrea

# add some extra output info and some details to stderr
DEBUG = False

# lines to ancestors
line_colors = ['orchid', 'tomato', 'lightseagreen']
line_colors.extend( ['chocolate', 'forestgreen', 'darkorange', 'teal'] )
line_colors.extend( ['yellowgreen', 'coral', 'royalblue', 'salmon'] )

# box containing a match person
match_color = 'springgreen'

# the box for "me"
me_color = 'lightblue'

# multiple marriage outline
multi_marr_color = '#ffc000'  #golden yellow

# use this for a missing partner in a family union
missing_name = 'unknown'

# I tend to list the wife first, the displar ordering can be changed by
# swapping the names in this list
partner_types = [ 'wife', 'husb' ]


def get_version():
    return '7.5'


def load_my_module( module_name, relative_path ):
    """
    Load a module in my own single .py file. Requires Python 3.6+
    Give the name of the module, not the file name.
    Give the path to the module relative to the calling program.
    Requires:
        import importlib.util
        import os
    Use like this:
        readgedcom = load_my_module( 'readgedcom', '../libs' )
        data = readgedcom.read_file( input-file )
    """
    assert isinstance( module_name, str ), 'Non-string passed as module name'
    assert isinstance( relative_path, str ), 'Non-string passed as relative path'

    file_path = os.path.dirname( os.path.realpath( __file__ ) )
    file_path += os.path.sep + relative_path
    file_path += os.path.sep + module_name + '.py'

    assert os.path.isfile( file_path ), 'Module file not found at ' + str(file_path)

    module_spec = importlib.util.spec_from_file_location( module_name, file_path )
    my_module = importlib.util.module_from_spec( module_spec )
    module_spec.loader.exec_module( my_module )

    return my_module


def get_program_options():
    results = dict()

    # left-to-right, top-to-bottom
    orientations = [ 'lr', 'tb', 'bt', 'rl' ]
    formats = ['tree', 'gedcom', 'matrix' ]
    eventtypes = [ 'note', 'value' ]
    # top-center/left/right bottom-center/left/right and reversed just in case
    placetitles = ['tc', 'tl', 'tr', 'bc', 'bl', 'br' ]
    other_placetitles = ['ct', 'lt', 'rt', 'cb', 'lb', 'rb']

    results['infile'] = None
    results['eventname'] = None
    results['eventtype'] = eventtypes[0]
    results['libpath'] = '.'
    results['min'] = 0
    results['max'] = 5000
    results['format'] = formats[0]
    results['reverse'] = False
    results['orientation'] = orientations[0]
    results['title'] = None
    results['relationship'] = False
    results['shortname'] = False
    results['placetitle'] = placetitles[0]
    results['thick'] = 1
    results['separate'] = False

    arg_help = 'Draw DNA matches.'
    parser = argparse.ArgumentParser( description=arg_help )

    arg_help = 'Show version then exit.'
    parser.add_argument( '--version', action='version', version=get_version() )

    arg_help = 'Minimum of matches (cM) to include. Default ' + str(results['min'])
    parser.add_argument( '--min', default=results['min'], type=int, help=arg_help )

    arg_help = 'Maximum of matches (cM) to include. Default ' + str(results['max'])
    parser.add_argument( '--max', default=results['max'], type=int, help=arg_help )

    arg_help = 'Format of output. Default ' + results['format']
    parser.add_argument( '--format', default=results['format'], choices=formats, help=arg_help )

    arg_help = 'For dot file output, reverse the order of the links.'
    parser.add_argument( '--reverse-arrows', default=results['reverse'], action='store_true', help=arg_help )

    arg_help = 'Orientation of the output dot file lr, tb, bt, rl; for for left-to-right, top-to-bottom, etc.'
    arg_help += ' Default:' + results['orientation']
    parser.add_argument( '--orientation', default=results['orientation'], type=str, help=arg_help )

    arg_help = 'Title to add to graph. Default is none.'
    parser.add_argument( '--title', default=results['title'], type=str, help=arg_help )

    arg_help = 'Placement of the title: tc, tl, tr, bc, bl, br: for top-center, top-left, top-right, etc. Default is "tc".'
    parser.add_argument( '--placetitle', default=results['placetitle'], type=str, help=arg_help )

    arg_help = 'Show the relationship name for the matches.'
    parser.add_argument( '--relationship', default=results['relationship'], action='store_true', help=arg_help )

    arg_help = 'Show only the first word of given names.'
    parser.add_argument( '--shortname', default=results['shortname'], action='store_true', help=arg_help )

    arg_help = 'Style of data record holding the DNA data values.'
    arg_help += ' In the event note or the value.'
    arg_help += ' Default:' + results['eventtype']
    parser.add_argument( '--eventtype', default=results['eventtype'], type=str, help=arg_help )

    # this option can be repeated for extra thickness
    arg_help = 'Increase width of connecting lines'
    parser.add_argument( '--thick', action='count', help=arg_help )

    # in matrix format, separate immediate family from close family and 1C from 1C1R, 1C2R, etc.
    #arg_help = 'Separate cousins by removed count. in the matrix format.'
    #parser.add_argument( '--separate', default=results['separate'], action='store_true', help=arg_help )

    # maybe this should be changed to have a type which better matched a directory
    arg_help = 'Location of the gedcom library. Default is current directory.'
    parser.add_argument( '--libpath', default=results['libpath'], type=str, help=arg_help )

    parser.add_argument('eventname', type=str )
    parser.add_argument('infile', type=argparse.FileType('r') )

    args = parser.parse_args()

    results['eventname'] = args.eventname
    results['infile'] = args.infile.name
    results['libpath'] = args.libpath
    results['min'] = args.min
    results['max'] = args.max
    results['reverse'] = args.reverse_arrows
    results['relationship'] = args.relationship
    results['shortname'] = args.shortname

    # probably best to set as a constant rather than a user option
    # some info above, where the argument setup is commented out
    results['separate'] = True

    value = args.orientation.lower()
    if value in orientations:
       results['orientation'] = value

    value = args.format.lower()
    if value in formats:
       results['format'] = value

    value = args.eventtype.lower()
    if value in eventtypes:
       results['eventtype'] = value

    value = args.title
    if value:
       results['title'] = value.strip()

    value = args.placetitle.lower()
    if value in placetitles or value in other_placetitles:
       results['placetitle'] = value

    value = args.thick
    if value:
       results['thick'] += value

    # if output is gedcom, disable shortname
    if results['format'] == 'gedcom':
       results['shortname'] = False
       results['relationship'] = False

    return results


def show_items( title, the_list ):
    print( title, file=sys.stderr )
    for item in the_list:
        print( '    ', item, the_list[item], file=sys.stderr )


def find_relation_label( me, them ):
    # return a string of the relationship of "them" to "me"
    # as "grandparent", "1C", "auncle", etc
    # given the generation distance to the nearest common ancestor family
    #
    # Note the use of non-gender specific labels
    # "auncle" = "aunt or uncle"
    # "nibling" = "niece or nephew"
    #
    # Note that the labels used here must be the same as in the dna-range setup.

    result = 'N/A'

    if them == 0:
       # direct line
       if me == 0:
          result = 'self'
       elif me == 1:
          result = 'parent'
       elif me == 2:
          result = 'grandparent'
       else:
          result = 'g' * (me - 2) + '-grandparent'

    elif me == 0:
         # direct line
         if them == 0:
            result = 'self'
         elif them == 1:
            result = 'child'
         elif them == 2:
            result = 'grandchild'
         else:
            result = 'g' * (them - 2) + '-grandchild'

    elif me == 1:
         if them == 1:
            result = 'sibling'  #or half-sibling by checking parents family
         elif them == 2:
            result = 'nibling'
         elif them == 3:
            result = 'grandnibling'
         else:
            result = 'g' * (them - 3) + '-grandnibling'

    elif me == them:
         if me == 0:
            result = 'self'
         elif me == 1:
            result = 'sibling' #or half-sibling
         else:
            result = str(me - 1) + 'C'

    elif them == 1:
         if me == 2:
            result = 'auncle'
         elif me == 3:
            result = 'grandauncle'
         else:
            result = 'g' * (me - 3) + '-grandauncle'

    elif me == 2:
        result = '1C' + str(them - 2) + 'R'

    elif me > 2:
         y = abs( them - me )
         if them < me:
            # older generation
            result = str(them - 1) + 'C' + str(y) + 'R'
         else:
            # younger generation
            result = str(me - 1) + 'C' + str(y) + 'R'

    return result


def compute_relation( closest ):
    gen_me = len( closest['match-path'] )
    gen_them = len( closest['path'] )
    half = ''
    if closest['fam'] != closest['match-fam']:
       half = 'half-'
    return half + find_relation_label( gen_me, gen_them )


def extract_dna_cm( indi, note ):
    """ Return the numeric cM value from the note which is
        a number at the start of the line followed by "cM" or "cm" """

    def string_is_numeric( x ):
        result = True
        try:
           y = float( x )
        except ValueError:
           result = False
        return result

    xref = '@I' + str( data[i_key][indi]['xref'] ) + '@'

    s = note.replace('  ',' ').strip().lower()

    result = None

    parts = s.split()
    if len(parts) > 1:
       if parts[1].startswith('cm') and (parts[1] == 'cm' or parts[1][2] in [' ','.',',',';',':']):
          # assume anglo numbers with commas but not euro style "1.234,56"
          number = parts[0].replace(',','')
          if string_is_numeric( number ):
             result = float( number )
             if result < 0:
                # but not bothering to check for an upper bound
                result = None
                print( xref, 'Ignoring invalid DNA value (below zero):', note, file=sys.stderr )
             else:
                result = int( round( result ) )
          else:
             print( xref, 'Ignoring unusable DNA value:', note, file=sys.stderr )
       else:
          print( xref, 'Ignoring unusable DNA value:', note, file=sys.stderr )

    return result



def get_xref( individual ):
    return 'i' + str( individual['xref'] )


def get_name( individual ):
    """ Return the name for the individual in the passed data section. """
    name = individual['name'][0]['html']
    if options['shortname']:
       shortened = ''
       if 'givn' in individual['name'][0]:
          shortened = individual['name'][0]['givn_html'].split(' ')[0] + ' '
       if 'surn' in individual['name'][0]:
          shortened += individual['name'][0]['surn_html']
       if shortened.strip():
          name = shortened.strip()
    name = name.replace( '/', '&sol;' ).replace('"','&quot;').replace("'","&rsquo;").strip()
    # the standard unknown code is not good for svg output
    if '?' in name and '[' in name and ']' in name:
       name = 'unknown'
    if DEBUG:
       name += ' ' + get_xref( individual )
    return name


def check_for_dna_event( dna_event, value_key, individual ):
    """ Does the person in data section contain the desired dna event.
        Return the found value. "None" means there is no such event. """
    result = None
    if 'even' in individual:
       for event in individual['even']:
           if event['type'].lower() == dna_event.lower():
              if value_key in event:
                 result = event[value_key].strip()
              break
    return result


def does_fam_have_match( matches, family ):
    # Does the family contain a person which is a match
    result = False
    for parent in partner_types:
        if parent in family:
           if family[parent][0] in matches:
              result = True
              break
    return result


def begin_ged():
    print( '0 HEAD' )
    print( '1 SOUR draw-dna-matches' )
    print( '1 GEDC' )
    print( '2 VERS 5.5.1' )
    print( '2 FORM LINEAGE-LINKED' )
    print( '1 CHAR UTF-8' )
    print( '1 SUBM @SUB1@' )
    print( '0 @SUB1@ SUBM' )
    print( '1 NAME draw-dna-matches' )

def end_ged():
    print( '0 TRLR' )


def make_ged_id( s ):
    return s.replace('@','').replace('I','').replace('i','').replace('F','').replace('f','')


def ged_individuals( families, people ):
    # bare minimum information getting saved

    def show_event( tag, indi_data ):
        if tag in indi_data:
           best = 0
           if readgedcom.BEST_EVENT_KEY in indi_data:
              if tag in indi_data[readgedcom.BEST_EVENT_KEY]:
                 best = indi_data[readgedcom.BEST_EVENT_KEY][tag]
           if 'date' in indi_data[tag][best]:
              print( '1', tag.upper() )
              print( '2 DATE', indi_data[tag][best]['date']['in'] )

    def show_family( tag, indi_data ):
        if tag in indi_data:
           for fam in indi_data[tag]:
               if fam in families:
                  print( '1', tag.upper(), '@F' + make_ged_id(fam) + '@' )

    for indi in people:
        print( '0 @I' + make_ged_id(indi) + '@ INDI' )
        print( '1 NAME', data[i_key][indi]['name'][0]['value'] )
        show_event( 'birt', data[i_key][indi] )
        show_event( 'deat', data[i_key][indi] )

        show_family( 'fams', data[i_key][indi] )
        show_family( 'famc', data[i_key][indi] )

        # and must include the dna data
        tag = 'even'
        if tag in data[i_key][indi]:
           for event in data[i_key][indi][tag]:
               if 'type' in event and event['type'] == options['eventname']:
                  if 'note' in event:
                     print( '1 EVEN' )
                     print( '2 TYPE', options['eventname'] )
                     print( '2 NOTE', event['note'] )


def ged_families( families, people ):
    already_seen = []
    for fam in families:
        if fam in already_seen:
           continue
        already_seen.append( fam )
        print( '0 @F' + make_ged_id(fam) + '@ FAM' )
        for parent in partner_types:
            if parent in data[f_key][fam]:
               # only taking the zero'th person as the parent,
               # maybe shold check all of them
               indi = data[f_key][fam][parent][0]
               print( '1', parent.upper(), '@I' + make_ged_id(indi) + '@')
        tag = 'chil'
        if tag in data[f_key][fam]:
           for child in data[f_key][fam][tag]:
               if child in people:
                  print( '1 CHIL @I' + make_ged_id(child) + '@' )


def make_dot_id( xref ):
    return xref.lower().replace('@','').replace('i','').replace('f','').replace('.','')

def make_fam_dot_id( fam ):
    # requires use of readgedcom v1.14.0+
    return 'f' + make_dot_id( str(data[f_key][fam]['xref']) )

def make_indi_dot_id( indi ):
    # requires use of readgedcom v1.14.0+
    return 'i' + make_dot_id( str(data[i_key][indi]['xref']) )


def begin_dot_title( title, title_placement ):
    if title:
       print( 'label="' + title + '";' )
       # default is t for top
       if 't' in title_placement:
          print( 'labelloc="t";' )
       if 'b' in title_placement:
          print( 'labelloc="b";' )
       # default is c for center
       if 'l' in title_placement:
          print( 'labeljust="l";' )
       elif 'r' in title_placement:
          print( 'labeljust="r";' )


def begin_dot( orientation, thickness, title, title_placement ):
    """ Start of the DOT output file """
    print( 'digraph family {' )
    print( 'node [shape=plaintext];' )
    print( 'edge [penwidth=' + str( thickness ) + '];' )
    print( 'rankdir=' + orientation.upper() + ';' )
    begin_dot_title( title, title_placement )


def end_dot():
    """ End of the DOT output file """
    print( '}' )


def begin_dot_matrix( start_indi, title, title_placement ):
    # should convert this to a here document
    start_name = get_name( data[i_key][start_indi] )

    print( 'digraph DNA_matches {' )

    begin_dot_title( title, title_placement )

    print( '  node [' )
    print( '  style = "setlinewidth(2)",' )
    print( '  fontsize = 11, height = 1,' )
    print( '  shape = box, width = 1 ]' )
    print( '' )
    print( 'subgraph self {' )
    print( '  graph [rank = same]' )
    print( '  edge [style = invis];' )
    print( '  self_label [' )
    print( '     label = "' + start_name + '",' )
    print( '     height = 1,' )
    print( '     row = top' )
    print( '  ];' )
    print( '}' )

def end_dot_matrix():
    print( '}' )


def add_matrix( matches, displayed, more_separation, show_relationship ):
    # gather people by relationship
    relations = dict()

    # regexp for cousin numbers
    # 1C, 2C, 2C1R, etc.
    cousin_pattern = re.compile( r'^(\d\d*)C' )

    immediate_relation_key = 'immediate'
    close_relation_key = 'close'

    def collect_relation( i, relation_name ):
        if relation_name not in relations:
           relations[relation_name] = []
        relations[relation_name].append( i )

    def output_relations( graph_name, prev_graph_name, color, relation_type ):
        print( '' )

        # sort by dna match size
        # the lists are not large so performance is not a concern
        match_sizes = dict()
        for indi in relations[relation_type]:
            # first part of the note should be the dna cM match count
            # and it might be a non-integer numberr
            match_size = float( matches[indi]['note'].split(' ')[0] )
            # numeric precision is not a concern
            if match_size not in match_sizes:
               match_sizes[match_size] = []
            match_sizes[match_size].append( indi )

        label = relation_type
        # special case
        if label in [immediate_relation_key,close_relation_key]:
           label += '\\nfamily'

        print( ' subgraph', graph_name, '{' )
        print( '   graph [rank = same]' )
        print( '   node [color="' + color + '"]' )
        print( '   edge [style = invis];' )
        print( '  ', graph_name + '_label [' )
        print( '      label = "' + label + '",' )
        print( '      height = 0.5,' )
        print( '      row = top' )
        print( '   ];' )

        n = 0
        prev_node = graph_name + '_label'

        for match_size in reversed(sorted( match_sizes.keys() )):
            for indi in match_sizes[match_size]:
                n += 1
                node_name = graph_name + '_' + str( n )
                indi_info = get_name( data[i_key][indi] )
                if show_relationship and 'relation' in matches[indi]:
                   indi_info += '\\n' + matches[indi]['relation']
                indi_info += '\\n' + matches[indi]['note']
                print( '  ', node_name, '[label="' + indi_info + '"]' )
                print( '  ', prev_node, '->', node_name )
                prev_node = node_name

        print( ' }' )
        print( '' )
        print( prev_graph_name + '_label', '->', graph_name + '_label' )

    for indi in matches:
        # the 'relation' valus is 'sibling', '1C', '2C1R', etc
        # which is how people are going to be grouped

        if 'relation' in matches[indi]:
           displayed.add( indi )
           # don't bother breaking out the half relations from full relations
           relation = matches[indi]['relation'].upper().replace( 'HALF-', '' )
           m = cousin_pattern.match( relation )
           if m:
              cousin = m.group(1)
              relation_key = cousin + 'C'
              if more_separation:
                 # then care more about the cousin removal count, if there is one
                 relation_key = relation
              collect_relation( indi, relation_key )

           else:
              # must be a parent or child or auncle or other non-cousin
              relation_key = close_relation_key
              if more_separation and relation.lower() in ['parent','sibling','child']:
                 relation_key = immediate_relation_key
              collect_relation( indi, relation_key )


    n_color = 0

    # first is the name of the selected person
    prev_graph = 'self'

    # closer than cousins (parent, sibling, aunt/uncle, etc)
    for relation_key in [immediate_relation_key, close_relation_key]:
        if relation_key in relations:
           n_color = ( n_color + 1 ) % len( line_colors )
           output_relations( relation_key, prev_graph, line_colors[n_color], relation_key )
           prev_graph = relation_key

    # then actual cousins by skipping the close family
    # and lexical sorting by key name so that 1C, 1C1R, 2C1R, 2C3R, 3C are displayed in order

    for relation in sorted(list(relations.keys())):
        if relation not in [immediate_relation_key, close_relation_key]:
           # graph name doesn't alllow names with leading digits
           graph_name = 'g' + relation
           n_color = ( n_color + 1 ) % len( line_colors )
           output_relations( graph_name, prev_graph, line_colors[n_color], relation )
           prev_graph = graph_name


def dot_labels( matches, fam_to_show, people_to_show, married_multi, fam_names, me_id, show_relationship ):
    """ Output a label for each person who appears in the graphs.
        'matches' as created in the calling program.
        'fam_to_show' has a boolean value of a-partner-is-dna-matched
        'people_to_show' is a plain list
        'married_multi' is a list of those in more than one marriage
        'fam_names' is the ancestor families to show relation with 'me'
        'me_id' is id of main person

        See https://graphviz.org/doc/info/shapes.html
        section "Recreating the Record Example"
        Using HTML is the only way to apply color only one partner in a family.

        To make the pointers work with HTML the setup requires "node shape = plaintext"
        and then all labels everything needs to be HTML.
    """

    def output_label( dot_id, s ):
        text = '<\n<table cellpadding="3" border="1" cellspacing="0" cellborder="0">\n'
        text += s
        text += '</table>>'
        print( dot_id, '[label=' + text + '];' )

    def output_family_label( fam ):
        parent_ids = []
        text = ''
        add_sep = True

        for parent in partner_types:
            if parent in data[f_key][fam]:
               parent_id = data[f_key][fam][parent][0]
               parent_ids.append( parent_id )

               name = get_name( data[i_key][parent_id] )

               text += '<tr><td port="' + parent[0] + '"'
               if parent_id in matched:
                  box_color = match_color
                  if parent_id == me_id:
                     box_color = me_color

                  if parent_id in married_multi:
                     box_color = multi_marr_color

                  text += ' bgcolor="' + box_color + '">' + name
                  text += '<br/>' + matches[parent_id]['note']
                  if show_relationship and 'relation' in matched[parent_id]:
                     text += '<br/>' + matched[parent_id]['relation']
               else:
                  if parent_id in married_multi:
                     text += ' bgcolor="' + multi_marr_color + '"'
                  text += '>' + name
               text += '</td></tr>\n'

            else:
              # put something in for a missing parent record
              text += '<tr><td>' + missing_name + '</td></tr>\n'

            if add_sep:
               add_sep = False
               # "u" for "union"
               # shrink up this section
               smaller = ' cellpadding="0" cellspacing="0"'
               text += '<tr><td port="u"' + smaller + '>&amp;</td></tr>\n'

        if fam in fam_names:
           # add this relationship name
           relation = fam_names[fam]
           if relation:
              text += '<tr><td bgcolor="' + me_color + '">' + relation + '</td></tr>\n'

        output_label( make_fam_dot_id(fam), text )

        return parent_ids

    def output_indi_label( indi ):
        name = get_name( data[i_key][indi] )

        text = '<tr><td port="i"'
        if indi in matches:
           box_color = match_color
           if indi == me_id:
              box_color = me_color

           text += ' bgcolor="' + box_color + '">' + name
           text += '<br/>' + matches[indi]['note']
           if show_relationship and 'relation' in matched[indi]:
              text += '<br/>' + matches[indi]['relation']
        else:
           text += '>' + name
        text += '</td></tr>\n'

        output_label( make_indi_dot_id(indi), text )

    # use this to skip matches within families
    already_fam = set()
    already_indi = set()

    # families first

    for fam in fam_to_show:
        if fam not in already_fam:
           already_fam.add( fam )

           partners = output_family_label( fam )

           for partner in partners:
               already_indi.add( partner )

    # people who aren't in the families

    for indi in people_to_show:
        if indi not in already_indi:
           already_indi.add( indi )
           output_indi_label( indi )


def dot_connect( families_to_show, people_to_show, do_reverse ):
    """ Output the links from one person/family to the next. """

    def get_family_of_child( indi ):
        results = []
        key = 'famc'
        if key in data[i_key][indi]:
           results.append( data[i_key][indi][key][0] )
        return results

    # if this many incoming edges (or more), set a color on the edges
    n_to_color = 3

    # keep the routes from one family to the next
    # so that there is each one only once
    routes = set()

    # count the number of times a family is targeted
    fam_count = dict()

    already_indi = set()

    # families first

    for fam in families_to_show:
        # to the parents (if parent family is shown)
        for partner in partner_types:
            if partner in data[f_key][fam]:
               partner_id = data[f_key][fam][partner][0]
               source = make_fam_dot_id( fam ) + ':' + partner[0] #:w or :h as post
               # the partners in that source family can't be shown independantly
               already_indi.add( partner_id )
               for parent_fam in get_family_of_child( partner_id ):
                   if parent_fam in families_to_show:
                      target = make_fam_dot_id( parent_fam ) + ':u'
                      routes.add( (source, target) )

                      if target not in fam_count:
                         fam_count[target] = 0
                      fam_count[target] += 1

    # individuals

    for indi in people_to_show:
        if indi not in already_indi:
           source = make_indi_dot_id( indi ) + ':i'
           for parent_fam in get_family_of_child( indi ):
               if parent_fam in families_to_show:
                  target = make_fam_dot_id( parent_fam ) + ':u'
                  routes.add( (source, target) )

                  if target not in fam_count:
                     fam_count[target] = 0
                  fam_count[target] += 1

    # output the routes

    n_colors = len( line_colors )
    c = n_colors + 1

    # choose a color for family links
    colors = dict()
    for route in routes:
        target = route[1]
        if target in colors:
           continue
        colors[target] = ''
        # if to a family, test for need of a color change
        if target in fam_count:
           if fam_count[target] >= n_to_color:
              # pick the next color
              c += 1
              if c >= n_colors:
                 c = 0
              colors[target] = ' [color=' + line_colors[c] + ']'

    for route in routes:
        source = route[0]
        target = route[1]
        if do_reverse:
           print( target + ' -> ' + source + colors[target] + ';' )
        else:
           print( source + ' -> ' + target + colors[target] + ';' )


def find_ancestors( indi, path, ancestors ):
    """ Return the ancestors for the given person.
        As a dict of [ancestor] = { 'fam': family,
                                    'path': [ families to get to this person ]
                                  }
        Length of the path is the number of generations to the ancestor.
    """

    key = 'famc'
    if key in data[i_key][indi] and data[i_key][indi][key]:
       fam = data[i_key][indi][key][0]

       new_path = path + [fam]

       for partner in partner_types:
           if partner in data[f_key][fam]:
              ancestor = data[f_key][fam][partner][0]

              do_update = True
              if ancestor in ancestors:
                 # pick the shortest path
                 if len(ancestors[ancestor]['path']) < len(new_path):
                    do_update = False
              if do_update:
                 ancestors[ancestor] = { 'fam': fam, 'path':new_path }

              find_ancestors( ancestor, path + [fam], ancestors )


def find_common_ancestor( indi, base_person, base_ancestors ):
    """ Return the closest ancestor to the "base person" from "indi" in a dict.
    An empty result means no match, otherwise:

    result['indi'] = the ancestor who is the closest
    result['fam'] = fam containing the ancestor from which "base" is descendant
    result['path'] = path from base person to closest ancestor
    result['match-fam'] = fam containing the ancestor from which "indi" is descendant
    result['match-path'] = path from "indi" to the ancestor

    The double fam and path items are because the indi and base may be in a
    half-relation whereby they share one ancestor but are descendant from
    different families. I.E. fam not equal match-fam means half-relation.
    """

    result = dict()

    ancestors = dict()
    find_ancestors( indi, [], ancestors )

    if base_person in ancestors:
       # person is a direct descendant
       result['indi'] = base_person
       result['fam'] = ancestors[base_person]['fam'] # fam containing base person
       result['path'] = ancestors[base_person]['path'] # from descendant to base person
       result['match-fam'] = result['fam'] # same fam as above
       result['match-path'] = [] # base person to base person

    elif indi in base_ancestors:
       # person is a direct ancestor
       result['indi'] = indi
       result['fam'] = base_ancestors[indi]['fam'] # fam containing ancestor
       result['path'] = [] # base person to base person
       result['match-fam'] = result['fam'] # same fam as above
       result['match-path'] = base_ancestors[indi]['path'] # from base person to ancestor

    else:
       # pick a big number
       found_len = 1000000

       for ancestor in ancestors:
           if ancestor in base_ancestors:
              path_len = len( ancestors[ancestor]['path'] )
              if path_len == found_len:
                 # if no closer
                 # prefer same family over "half" relations with different families
                 them_fam = ancestors[ancestor]['fam']
                 base_fam = base_ancestors[ancestor]['fam']
                 if them_fam == base_fam:
                    # side effect is that without double checking
                    # this will toggle batween partners in a matched family
                    result['indi'] = ancestor
                    result['fam'] = them_fam
                    result['path'] = ancestors[ancestor]['path']
                    result['match-fam'] = base_fam
                    result['match-path'] = base_ancestors[ancestor]['path']
              elif path_len < found_len:
                 found_len = path_len
                 result['indi'] = ancestor
                 result['fam'] = ancestors[ancestor]['fam']
                 result['path'] = ancestors[ancestor]['path']
                 result['match-fam'] = base_ancestors[ancestor]['fam']
                 result['match-path'] = base_ancestors[ancestor]['path']

    return result


def find_families_of_multiple_marriages( people_to_show, families_to_show ):
    # for each person in multiple marriages return the list of their families
    # if the families are also being shown
    # result[indi1] = [fam1, fam2]
    # result[indi2] = [fam3, fam4]
    # etc.
    results = dict()

    for indi in people_to_show:
        key = 'fams'
        if key in data[i_key][indi]:
           for_this_person = set()
           for fam in data[i_key][indi][key]:
               if fam in families_to_show:
                  for_this_person.add( fam )
           if len(for_this_person) > 1:
              results[indi] = list(for_this_person)

    return results


options = get_program_options()

readgedcom = load_my_module( 'readgedcom', options['libpath'] )

# these are keys into the parsed sections of the returned data structure
i_key = readgedcom.PARSED_INDI
f_key = readgedcom.PARSED_FAM

data_opts = dict()
data_opts['display-gedcom-warnings'] = False
data_opts['exit-on-no-families'] = True
data_opts['exit-on-missing-individuals'] = True
data_opts['exit-on-missing-families'] = True
data_opts['only-birth'] = True

data = readgedcom.read_file( options['infile'], data_opts )

# people who have the dna event
# matched[indi] = { note: the event text, shared: closest shared ancestor )
matched = dict()

# the id of the base dna match person
me = None

# the event not existing is different from no extacted values
found_event = False

for indi in data[i_key]:
    result = check_for_dna_event( options['eventname'], options['eventtype'], data[i_key][indi] )
    if result is not None:
       found_event = True
       test_for_me = result.lower()
       if test_for_me.startswith('me') and (test_for_me == 'me' or test_for_me[2] in [' ', '.', ',', ':']):
          matched[indi] = dict()
          matched[indi]['note'] = 'me'
          me = indi
       else:
          value = extract_dna_cm( indi, result )
          if value is not None:
             if options['min'] <= value <= options['max']:
                matched[indi] = dict()
                matched[indi]['note'] = str(value) + ' cM'

if not found_event:
   event_name = '"' + options['eventname'] + '" / "' + options['eventtype'] + '"'
   print( 'Didn\'t locate anyone with the selected event', event_name, file=sys.stderr )
   sys.exit(1)

if not me:
   print( 'Didn\'t find base person', file=sys.stderr )
   sys.exit(1)

if len(matched) < 2:
   # one = me, so need 2 or more
   print( 'Didn\'t find anyone to match with', file=sys.stderr )
   sys.exit(1)

if DEBUG:
   print( '', file=sys.stderr )
   print( 'matches', file=sys.stderr )
   for indi in matched:
       show_items( indi, matched[indi] )

my_ancestors = dict()
find_ancestors( me, [], my_ancestors )

if DEBUG:
   print( '', file=sys.stderr )
   print( 'my ancestors(base person)', me, file=sys.stderr )
   for indi in my_ancestors:
       show_items( indi, my_ancestors[indi] )

for indi in matched:
    if indi == me:
       matched[indi]['common'] = None
    else:
       matched[indi]['common'] = find_common_ancestor( indi, me, my_ancestors )

if DEBUG:
   print( '', file=sys.stderr )
   print( 'matches, closest ancestor', file=sys.stderr )
   for indi in matched:
       if matched[indi]['common']:
          show_items( indi, matched[indi]['common'] )

# Add relationship names, always compute but the flag is if it should be shown

if DEBUG and options['relationship']:
   print( '', file=sys.stderr )
   print( 'relationships', file=sys.stderr )
for indi in matched:
    if matched[indi]['common']:
       matched[indi]['relation'] = compute_relation( matched[indi]['common'] )
       if DEBUG and options['relationship']:
          print( '   ', indi, matched[indi]['relation'], file=sys.stderr )

# For display purposes find all the families in all the paths.
# Value for family will be True if one of the partners is also a dna match.

families_to_display = dict()

for indi in matched:
    if matched[indi]['common']:
       path_fams = [] # used below
       for key in ['fam','match-fam']:
           fam = matched[indi]['common'][key]
           families_to_display[fam] = False
           path_fams.append( fam )
       for key in ['path','match-path']:
           for fam in matched[indi]['common'][key]:
               families_to_display[fam] = False

       # for half relationships, step to one older generation to ensure
       # the paths are connected
       if path_fams[0] != path_fams[1]:
          common = matched[indi]['common']['indi']
          key = 'famc'
          if key in data[i_key][common]:
             fam = data[i_key][common][key][0]
             families_to_display[fam] = False

# do the test

for fam in families_to_display:
    families_to_display[fam] = does_fam_have_match( matched, data[f_key][fam] )


# Add relationship names for ancestors which are common ancestors
if DEBUG and options['relationship']:
   print( '', file=sys.stderr )
   print( 'ancestor relationships', file=sys.stderr )

# Find all the common families
common_fams = dict()

for indi in matched:
    if indi != me:
       ancestor = matched[indi]['common']['indi']
       fam = matched[indi]['common']['match-fam']
       path_len = len( matched[indi]['common']['match-path'] )
       # make plural for both parents in family
       common_fams[fam] = find_relation_label( path_len, 0 ) + 's'

for fam in common_fams:
    # Skip the family if one partner is also a DNA match
    # because the relationship is already set to be shown for that person
    if families_to_display[fam]:
       common_fams[fam] = None

if DEBUG:
   print( '', file=sys.stderr )
   show_items( 'families_to_display', families_to_display )

# For display purposes find the people who are in the families in the paths
# Including those who are matches even don't have their own family

people_to_display = set()
people_to_display.add( me )
for indi in matched:
    if matched[indi]['common']:
       people_to_display.add( indi )
for fam in families_to_display:
    for partner in partner_types:
        if partner in data[f_key][fam]:
           people_to_display.add( data[f_key][fam][partner][0] )

if DEBUG:
   print( '', file=sys.stderr )
   print( 'people_to_display', people_to_display, file=sys.stderr )

multiple_marriages = find_families_of_multiple_marriages( people_to_display, families_to_display )

if DEBUG:
   if multiple_marriages:
      print( '', file=sys.stderr )
      show_items( 'multiply married', multiple_marriages )

# Output to stdout

if options['format'] == 'gedcom':
   begin_ged()
   ged_individuals( families_to_display, people_to_display )
   ged_families( families_to_display, people_to_display )
   end_ged()

elif options['format'] == 'matrix':
   # no families or connections, just the names grouped by relationship
   # and sorted by match size
   begin_dot_matrix( me, options['title'], options['placetitle'] )
   add_matrix( matched, people_to_display, options['separate'], options['relationship'] )
   end_dot_matrix()

else:

   begin_dot( options['orientation'], options['thick'], options['title'], options['placetitle'] )
   dot_labels( matched, families_to_display, people_to_display, multiple_marriages, common_fams, me, options['relationship'] )
   dot_connect( families_to_display, people_to_display, options['reverse'] )
   end_dot()

# DNA matched but not displayed
not_displayed = []
for indi in matched:
    if indi not in people_to_display:
       not_displayed.append( indi )
if not_displayed:
   if DEBUG:
      print( '', file=sys.stderr )
   print( 'Matches who are not displayed.', file=sys.stderr )
   print( 'Due to missing birth family or common ancestor above tree top.', file=sys.stderr )
   name = get_name( data[i_key][indi] ).strip()
   if not DEBUG:
      name += ' ' + get_xref( data[i_key][indi] ).strip()
   print( name, matched[indi]['note'], file=sys.stderr )
