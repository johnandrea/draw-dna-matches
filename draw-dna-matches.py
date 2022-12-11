#!/usr/local/bin/python3
import sys
import re
import argparse
import importlib.util
import os

# Output DNA matches in a tree view in Graphviz DOT format.
# Given a GEDCOM with people having a custom event of name as input
# and an optional note containing the cM value.
# The person for whom the matches are compared should have a note or value
# beginning with 'Me,'
#
# An example of a section in a gedcom file:
# 1 EVEN Ancestry
# 2 TYPE dnamatch
# 2 DATE BEF 2021
# 2 NOTE 290 cM across 15 segments
#
# Might not handle the situation where the closest shared family between
# two people doesn't exist in the data.
#
# This code is released under the MIT License: https://opensource.org/licenses/MIT
# Copyright (c) 2022 John A. Andrea

# add some extra output info and some details to stderr
DEBUG = False

# Within the event, 'note' or 'value' where the data is stored.
EVENT_ITEM = 'note'

# lines to ancestors
line_colors = ['orchid', 'tomato', 'lightseagreen']
line_colors.extend( ['gold', 'royalblue', 'coral'] )
line_colors.extend( ['yellowgreen', 'chocolate', 'salmon'] )

# box containing a match person
match_color = 'springgreen'

# the box for "me"
me_color = 'lightblue'

# multiple marriage outline
multi_marr_color = 'orange'


def show_version():
    print( '5.0' )


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

    results['version'] = False
    results['infile'] = None
    results['eventname'] = None
    results['libpath'] = '.'
    results['min'] = 0
    results['max'] = 5000
    results['format'] = 'dot'

    arg_help = 'Draw DNA matches.'
    parser = argparse.ArgumentParser( description=arg_help )

    arg_help = 'Show version then exit.'
    parser.add_argument( '--version', default=results['version'], action='store_true', help=arg_help )

    arg_help = 'Minimum of matches (cM) to include. Default ' + str(results['min'])
    parser.add_argument( '--min', default=results['min'], type=int, help=arg_help )

    arg_help = 'Maximum of matches (cM) to include. Default ' + str(results['max'])
    parser.add_argument( '--max', default=results['max'], type=int, help=arg_help )

    arg_help = 'Format of output. Default ' + results['format']
    formats = [ results['format'], 'gedcom' ]
    parser.add_argument( '--format', default=results['format'], choices=formats, help=arg_help )

    # maybe this should be changed to have a type which better matched a directory
    arg_help = 'Location of the gedcom library. Default is current directory.'
    parser.add_argument( '--libpath', default=results['libpath'], type=str, help=arg_help )

    parser.add_argument('eventname', type=str )
    parser.add_argument('infile', type=argparse.FileType('r') )

    args = parser.parse_args()

    results['version'] = args.version
    results['eventname'] = args.eventname
    results['infile'] = args.infile.name
    results['libpath'] = args.libpath
    results['min'] = args.min
    results['max'] = args.max
    results['format'] = args.format

    return results


def show_items( title, the_list ):
    print( title, file=sys.stderr )
    for item in the_list:
        print( '    ', item, the_list[item], file=sys.stderr )


def remove_numeric_comma( s ):
    """ Given 1,234 1,234,567 and similar, remove the comma.
        Does the same for all such patterns in the string.
        Assuming anglo style numbers rather than euro style of 1.234,99 """

    comma_pattern = re.compile( r'\d,\d' )

    result = s

    # global replace count not working on this expression,
    # use a loop as a workaround

    while comma_pattern.search( result ):
          result = re.sub( r'^(.*\d),(\d.*)$', r'\1\2', result )

    return result


def extract_dna_cm( note ):
    """ Return the numeric cM value from the note which is either just
        a number or a number followed by "cM" or "cm" """

    contains_a_number = re.compile( r'[0-9]' )
    just_a_number = re.compile( r'^[0-9]+$' )
    cm_count = re.compile( r'([0-9]+)\s*cm\W' )

    s = note.strip()

    result = ''

    if contains_a_number.search( s ):
       s = remove_numeric_comma( s )
       if just_a_number.search( s ):
          result = s
       else:
          # append a space for a simpler regexp of the word ending
          match = cm_count.search( s.lower() + ' ' )
          if match:
             result = match.group(1)

    return result


def get_name( individual ):
    """ Return the name for the individual in the passed data section. """
    name = individual['name'][0]['value']
    if DEBUG:
       name += ' i' + str( individual['xref'] )
    # the standard unknown code is not good for svg output
    if '?' in name and '[' in name and ']' in name:
       name = 'unknown'
    return name.replace( '/', '' ).replace('"','&quot;').replace("'","&rsquo;")


def check_for_dna_event( dna_event, value_key, individual ):
    """ Does the person in data section contain the
        desired dna event. Return a list with found or not. """
    result = [ False, '' ]
    if 'even' in individual:
       for event in individual['even']:
           if event['type'].lower() == dna_event.lower():
              if value_key in event:
                 result[0] = True
                 result[1] = event[value_key].strip()
              break
    return result


def does_fam_have_match( matches, family ):
    # Does the family contain a person which is a match
    result = False
    for parent in ['husb','wife']:
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
        for parent in ['wife','husb']:
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

def make_fam_dot_id( xref ):
    return 'f' + make_dot_id( str(xref) )

def make_indi_dot_id( xref ):
    return 'i' + make_dot_id( str(xref) )


def begin_dot():
    """ Start of the DOT output file """
    print( 'digraph family {' )
    print( 'rankdir=LR;')


def end_dot():
    """ End of the DOT output file """
    print( '}' )


def dot_labels( matches, fam_to_show, people_to_show, me_id ):
    """ Output a label for each person who appears in the graphs.
        'matches' as created in the calling program.
        'fam_to_show' has a boolean value of a-partner-is-dna-matched
        'people_to_show' is a plain list
        'me_id' is id of main person
    """

    def output_label( dot_id, s, extra ):
        print( dot_id, '[label=' + s.replace("'",'.') + extra + '];' )

    def output_plain_family_label( fam, multiplied_marr ):
        parent_ids = []
        text = ''
        sep = ''
        for parent in ['wife','husb']:
            if parent in data[f_key][fam]:
               parent_id = data[f_key][fam][parent][0]
               parent_ids.append( parent_id )
               text += sep + get_name( data[i_key][parent_id] )
               sep = '\\n+ '
        options = ''
        if multiplied_marr:
           options = ', color=' + multi_marr_color
        output_label( make_fam_dot_id(fam), '"'+ text +'"', options )
        return parent_ids

    def output_match_family_label( fam, multiplied_marr ):
        parent_ids = []
        text = '<\n<table cellpadding="2" cellborder="0" cellspacing="0" border="0">'
        sep = ''
        for parent in ['wife','husb']:
            if parent in data[f_key][fam]:
               parent_id = data[f_key][fam][parent][0]
               parent_ids.append( parent_id )
               # add padding
               name = ' ' + sep + get_name( data[i_key][parent_id] ) + ' '
               tr = '\n<tr><td'
               if parent_id in matches:
                  box_color = match_color
                  if parent_id == me_id:
                     box_color = me_color
                  td = tr + ' bgcolor="' + box_color + '">'
                  text += td + name + '</td></tr>'
                  text += td + matches[parent_id]['note'] + '</td></tr>'
               else:
                  text += tr + ' border="1">' + name + '</td></tr>'
               sep = '+ '
        text += '\n</table>\n>'
        options = ', shape="none"'
        if multiplied_marr:
           options += ', color=' + multi_marr_color
        output_label( make_fam_dot_id(fam), text, options )
        return parent_ids

    def output_indi_label( indi ):
        # note the escaped newlines
        text = get_name( data[i_key][indi] ) + '\\n' + matches[indi]['note']
        box_color = match_color
        if indi == me_id:
           box_color = me_color
        options = ', shape="record", style=filled, color=' + box_color
        output_label( make_indi_dot_id(indi), '"'+ text +'"', options )

    def find_families_of_multiple_marriages():
        results = []
        person_in_fams = dict()
        # get a list of the families for each person
        # if a family is in the shown families
        for indi in people_to_show:
            person_in_fams[indi] = []
            key = 'fams'
            if key in data[i_key][indi]:
               for fam in data[i_key][indi][key]:
                   if fam in fam_to_show:
                      person_in_fams[indi].append( fam )

        # count up the number of shown families each person has
        # and more than one indicates multiples
        for indi in person_in_fams:
            if len( person_in_fams[indi] ) > 1:
               for fam in person_in_fams[indi]:
                   if fam not in results:
                      results.append( fam )

        return results

    multiple_marriages = find_families_of_multiple_marriages()

    # use this to skip matches within families
    already_fam = set()
    already_indi = set()

    # families first

    for fam in fam_to_show:
        if fam not in already_fam:
           already_fam.add( fam )

           multiple_marr = fam in multiple_marriages
           partners = []

           if fam_to_show[fam]:
              partners = output_match_family_label( fam, multiple_marr )
           else:
              partners = output_plain_family_label( fam, multiple_marr )

           for partner in partners:
               already_indi.add( partner )

    # people who aren't in the families

    for indi in people_to_show:
        if indi not in already_indi:
           already_indi.add( indi )
           output_indi_label( indi )


def dot_connect( families_to_show, people_to_show ):
    """ Output the links from one person/family to the next. """

    def get_family_of_child( indi ):
        results = []
        key = 'famc'
        if key in data[i_key][indi]:
           results.append( data[i_key][indi][key][0] )
        return results

    def get_partner_ids( fam ):
        results = []
        for partner in ['wife','husb']:
            if partner in data[f_key][fam]:
               results.append( data[f_key][fam][partner][0] )
        return results

    def get_parent_families( fam ):
        results = []
        for partner in get_partner_ids( fam ):
            for child_fam in get_family_of_child( partner ):
                results.append( child_fam )
        return results


    # if this many incoming edges (or more), set a color on the edges
    n_to_color = 3

    # keep the routes from one family to the next
    # each one only once
    routes = set()

    # count the number of times a family is targeted
    fam_count = dict()

    already_indi = set()

    # families first

    for fam in families_to_show:
        # to the parents (if parent family is shown)
        source = make_fam_dot_id( fam )
        for parent_fam in get_parent_families( fam ):
            if parent_fam in families_to_show:
               target = make_fam_dot_id( parent_fam )
               routes.add( (source, target) )

               if target not in fam_count:
                  fam_count[target] = 0
               fam_count[target] += 1

               # the partners in that source family can't be shown independantly
               for partner in get_partner_ids( fam ):
                   already_indi.add( partner )

    # individuals

    for indi in people_to_show:
        if indi not in already_indi:
           source = make_indi_dot_id( indi )
           for parent_fam in get_family_of_child( indi ):
               if parent_fam in families_to_show:
                  target = make_fam_dot_id( parent_fam )
                  routes.add( (source, target) )

                  if target not in fam_count:
                     fam_count[target] = 0
                  fam_count[target] += 1

    # output the routes

    n_colors = len( line_colors )
    c = n_colors + 1

    for route in routes:
        source = route[0]
        target = route[1]

        extra = ''

        # if to a family, test for need of a color change
        if target in fam_count:
           if fam_count[target] >= n_to_color:
              # pick the next color
              c += 1
              if c >= n_colors:
                 c = 0

              extra = ' [color=' + line_colors[c] + ']'

        print( source + ' -> ' + target + extra + ';' )


def find_ancestors( indi, path ):
    """ Return the ancestors for the given person.
        As a dict of [ancestor] = { 'fam': family,
                                    'path': [ families to get to this person ]
                                  }
        Length of the path is the number of generations to the ancestor.

    """
    results = dict()
    key = 'famc'
    if key in data[i_key][indi]:
       # assuming blood relations are at index zero
       fam = data[i_key][indi][key][0]

       for partner in ['husb','wife']:
           if partner in data[f_key][fam]:
              partner_id = data[f_key][fam][partner][0]
              results[partner_id] = { 'fam': fam, 'path':path }
              ancestor_results = find_ancestors( partner_id, path + [fam] )
              for ancestor in ancestor_results:
                  # checking for existance will ensure only one path
                  if ancestor not in results:
                     results[ancestor] = ancestor_results[ancestor]
    return results


options = get_program_options()

if options['version']:
   show_version()
   sys.exit( 0 )

if not os.path.isdir( options['libpath'] ):
   print( 'Path to readgedcom is not a directory.', file=sys.stderr )
   sys.exit( 1 )

readgedcom = load_my_module( 'readgedcom', options['libpath'] )

# these are keys into the parsed sections of the returned data structure
i_key = readgedcom.PARSED_INDI
f_key = readgedcom.PARSED_FAM

opts = dict()
opts['display-gedcom-warnings'] = False

data = readgedcom.read_file( options['infile'], opts )

# people who have the dna event
# matched[indi] = { note: the event text, shared: closest shared ancestor )
matched = dict()

# the id of the base dna match person
me = None

for indi in data[i_key]:
    result = check_for_dna_event( options['eventname'], EVENT_ITEM, data[i_key][indi] )
    if result[0]:
       if result[1].lower().startswith( 'me,' ):
          matched[indi] = dict()
          matched[indi]['note'] = 'me'
          me = indi
       else:
          value = int( extract_dna_cm( result[1] ) )
          if options['min'] <= value <= options['max']:
             matched[indi] = dict()
             matched[indi]['note'] = str(value) + ' cM'

if not me:
   print( 'Didnt find base person', file=sys.stderr )
   sys.exit()

ancestors = dict()
# 'me' is included in the matched list
for indi in matched:
    ancestors[indi] = find_ancestors( indi, [] )

if DEBUG:
   print( '', file=sys.stderr )
   print( 'ancestors', file=sys.stderr )
   for indi in ancestors:
       if indi == me:
          print( 'me =', indi, file=sys.stderr )
       show_items( indi, ancestors[indi] )

# how many generations in the tree
# pick a big number
max_gen = 1000000

# For each of the dna matched people,
# find the closest family shared with me.
# If not found then the match can't be displayed which is ok
# because the display styles need to have that connection.

for indi in matched:
    if indi == me:
       continue

    found_gen = max_gen
    found_fam = None

    # is this person a direct ancestor of 'me'
    if indi in ancestors[me]:
       found_fam = ancestors[me][indi]['fam']

    else:
       # is this person a direct descendent of 'me'
       if me in ancestors[indi]:
          found_fam = ancestors[indi][me]['fam']

       else:
          for ancestor in ancestors[indi]:
              ancestor_fam = ancestors[indi][ancestor]['fam']
              for my_ancestor in ancestors[me]:
                  my_ancestor_fam = ancestors[me][my_ancestor]['fam']
                  if ancestor_fam == my_ancestor_fam:
                     gen_to_me = len( ancestors[me][my_ancestor]['path'] )
                     if gen_to_me < found_gen:
                        found_gen = gen_to_me
                        found_fam = ancestors[me][my_ancestor]['fam']

    if found_fam is not None:
       # the closest shared family
       matched[indi]['closest_fam'] = found_fam

if DEBUG:
   print( '', file=sys.stderr )
   print( 'matches, closest fam', file=sys.stderr )
   for indi in matched:
       show_items( indi, matched[indi] )

# For relationship calculations find closest shared ancestor
# which is different from closest family because of half-relationships.
# Unfortunately half-siblings would be skipped in this case.

for indi in matched:
    # ignore those without a found closest family because
    # they won't be output
    if 'closest_fam' not in matched[indi]:
       continue

    found_gen = max_gen
    found_ancestor = None
    fam_me = None
    gen_them = None
    fam_them = None

    # is this person a direct ancestor of 'me'
    if indi in ancestors[me]:
       gen_them = 0
       found_ancestor = indi
       fam_me = matched[indi]['closest_fam']
       found_gen = 1 + len( ancestors[me][indi]['path'] )
       fam_them = matched[indi]['closest_fam']

    else:
      # is this person a direct descendent of 'me'
      if me in ancestors[indi]:
         gen_them = 1 + len( ancestors[indi][me]['path'] )
         found_ancestor = me
         fam_me = matched[indi]['closest_fam']
         found_gen =  0
         fam_them = matched[indi]['closest_fam']

      else:
        for ancestor in ancestors[indi]:
            for my_ancestor in ancestors[me]:
                if ancestor == my_ancestor:
                   gen_to_me = 1 + len( ancestors[me][ancestor]['path'] )
                   if gen_to_me < found_gen:
                      found_ancestor = ancestor
                      found_gen = gen_to_me
                      gen_them = 1 + len( ancestors[indi][found_ancestor]['path'] )
                      fam_them = ancestors[indi][found_ancestor]['fam']
                      fam_me = ancestors[me][found_ancestor]['fam']


    if found_ancestor is not None:
       matched[indi]['closest_indi'] = dict()
       matched[indi]['closest_indi']['indi'] = found_ancestor
       matched[indi]['closest_indi']['gen_them'] = gen_them
       matched[indi]['closest_indi']['fam_them'] = fam_them
       matched[indi]['closest_indi']['gen_me'] = found_gen
       matched[indi]['closest_indi']['fam_me'] = fam_me

if DEBUG:
   print( '', file=sys.stderr )
   print( 'matches, closest indi', file=sys.stderr )
   for indi in matched:
       show_items( indi, matched[indi] )

# For display purposes find all the families in all the paths.
# Value for family will be True if one of the partners is also a dna match.

families_to_display = dict()

for indi in matched:
    if 'closest_fam' in matched[indi] and 'closest_indi' in matched[indi]:
       fam = matched[indi]['closest_fam']
       if fam not in families_to_display:
          families_to_display[fam] = False
       for item in ['fam_them','fam_me']:
           fam = matched[indi]['closest_indi'][item]
           if fam not in families_to_display:
              families_to_display[fam] = False
       shared_indi = matched[indi]['closest_indi']['indi']
       if shared_indi in ancestors[indi]:
          for fam in ancestors[indi][shared_indi]['path']:
              if fam not in families_to_display:
                 families_to_display[fam] = False

for fam in families_to_display:
    families_to_display[fam] = does_fam_have_match( matched, data[f_key][fam] )

# Likely possible to trim families at the top.
# If none above contain matches
# and if none of the matches link to anything above.

if DEBUG:
   print( '', file=sys.stderr )
   show_items( 'families_to_display', families_to_display )

# For display purposes find the people who are in the families in the paths
# including those who are matches even don't have their own family

people_to_display = set()
for indi in matched:
    if 'closest_fam' in matched[indi] and 'closest_indi' in matched[indi]:
       people_to_display.add( indi )

for fam in families_to_display:
    for partner in ['husb','wife']:
        if partner in data[f_key][fam]:
           people_to_display.add( data[f_key][fam][partner][0] )

if DEBUG:
   print( '', file=sys.stderr )
   print( 'people_to_display', people_to_display, file=sys.stderr )


# Output to stdout

if options['format'] == 'gedcom':
   begin_ged()
   ged_individuals( families_to_display, people_to_display )
   ged_families( families_to_display, people_to_display )
   end_ged()

else:
   begin_dot()

   dot_labels( matched, families_to_display, people_to_display, me )
   dot_connect( families_to_display, people_to_display )

   end_dot()
