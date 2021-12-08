#!/usr/local/bin/python3
import sys
import re
import readgedcom

# Output DNA matches in a tree view in Graphviz DOT format.
# Given a GEDCOM with people having an event of type 'dnamatch'
# and an optional note containing the cM value.
# The person for whom the matches are compared should have a note
# beginning with 'Me,'
#
# Might hot handle the situation where the closest shared family between
# two people doesn't exist in the data.


# This is the name of the event of value
EVENT_NAME = 'dnamatch'


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

    a_number = re.compile( r'[0-9]' )
    all_numbers = re.compile( r'^[0-9]+$' )
    cm_count = re.compile( r'([0-9]+)\s*cm\W' )

    s = note.strip()

    result = ''

    if a_number.search( s ):
       s = remove_numeric_comma( s )
       if all_numbers.search( s ):
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
    # the standard unknown code is not good for svg output
    #if readgedcom.UNKNOWN_NAME in name: #string match problem with non-ascii?
    if '?' in name and '[' in name and ']' in name:
       name = 'unknown'
    return name.replace( '/', '' )


def get_fam_name( family, individuals ):
    """ Return the name of the two people in the padded
        family data section. """
    name = ''
    sep = ''
    for parent in ['wife','husb']:
        if parent in family:
           parent_id = family[parent][0]
           name += sep + get_name( individuals[parent_id] )
           sep = '\\n& '
    return name


def check_for_dna_event( individual ):
    """ Does the person in data section contain the
        desired dna event. Return a list with found or not. """
    result = [ False, '' ]
    if 'even' in individual:
       for event in individual['even']:
           if event['type'].lower() == EVENT_NAME.lower():
              result[0] = True
              if 'note' in event:
                 result[1] = event['note'].strip()
              break
    return result


def all_ancestor_families_of( gen, start, indi, individuals, families ):
    """ Return a dict of all the ancestors of the given individual.
        Format is [indi_id] = gen  where gen is the number of genertions
        from the original start indvidual. """
    result = dict()
    if 'famc' in individuals[indi]:
       fam = individuals[indi]['famc'][0]
       result[fam] = gen
       for parent in ['wife','husb']:
           if parent in families[fam]:
              parent_id = families[fam][parent][0]
              # prevent a loop
              if parent_id != start:
                 result.update( all_ancestor_families_of( gen+1, start, parent_id, individuals, families ) )
    return result


def ancestor_families_of( indi, data ):
    """ See the called function. """
    return all_ancestor_families_of( 1, indi, indi, data[i_key], data[f_key] )


def find_ancestor_path( start, end_fam, individuals, families, path ):
    """ Return a list of the family ids from the start person to the end family.
        The list is in order of generations. The end family will be at the end
        of the list.
        Assuming that there are no loops in the families. """
    if 'famc' in individuals[start]:
       fam = individuals[start]['famc'][0]
       for parent in ['wife','husb']:
           if parent in families[fam]:
              parent_id = families[fam][parent][0]

              path.append( fam )

              if fam == end_fam:
                 return [ True, path ]

              # Try the next generation
              found = find_ancestor_path( parent_id, end_fam, individuals, families, path )
              if found[0]:
                 return found

              # This family doesn't lead to that ancestor
              path.pop()

    return [ False, path ]

def begin_dot():
    """ Start of the DOT output file """
    print( 'digraph family {' )
    print( 'node [shape=record];' )
    print( 'rankdir=LR;')


def end_dot():
    """ End of the DOT output file """
    print( '}' )


def dot_labels( individuals, families, matches, my_ancestors ):
    """ Output a label for each person who appears in the graphs. """

    def output_label( i, s, extra ):
        print( i, '[label="' + s.replace("'",'.') + '"' + extra + '];' )

    def more_labels( found, fam_list, list_of_multi ):
        for fam in fam_list:
            extra = ''
            if fam in list_of_multi:
               extra = ',color=orange'
            if fam not in found:
               output_label( fam, get_fam_name( families[fam], individuals ), extra )
               found[fam] = 1
        return found

    def check_multiple_person( fam, families, counter ):
        # return the families in which each person occurs
        for parent in ['wife','hush']:
            if parent in families[fam]:
               parent_id = families[fam][parent][0]
               if parent_id not in counter:
                  counter[parent_id] = []
               counter[parent_id].append( fam )

    def check_multiple_fam( person_counter ):
        # return the families which people appear in multiple families
        result = dict()
        # reduce the person families to a unique list
        for indi in person_counter:
            families = dict()
            for fam in person_counter[indi]:
                families[fam] = 1
            if len(families) > 1:
               for fam in families:
                   result[fam] = 1
        return result

    found = dict()

    # name of the dna people
    for indi in matches:
        if indi not in found:
           label = get_name( individuals[indi] ) + '\\n' + matches[indi]['note']
           output_label( indi, label, ',color=lightgreen,style=filled' )
           found[indi] = 1

    # find people who are in multiple marriages
    person_counter = dict()
    for indi in matches:
        if matches[indi]['path']:
           for fam in matches[indi]['path']:
               check_multiple_person( fam, families, person_counter )
    for indi in my_ancestors:
        for fam in my_ancestors[indi]:
            check_multiple_person( fam, families, person_counter )
    multiple_families = check_multiple_fam( person_counter )

    # now everyone in the paths
    for indi in matches:
        if matches[indi]['path']:
           found = more_labels( found, matches[indi]['path'], multiple_families )

    # then everyone in my paths to the same shared ancestors
    for indi in my_ancestors:
        found = more_labels( found, my_ancestors[indi], multiple_families )


def dot_connect( matches, me, my_paths ):
    """ Output the links from one family to the next. """

    line_colors = ['orchid', 'tomato', 'lightseagreen', 'gold', 'royalblue', 'coral']
    line_colors.extend( ['yellowgreen', 'chocolate', 'salmon', 'yellowgreen'] )

    # if this many or more incoming edges, set a color on the edges
    n_to_color = 3

    # keep the routes from one family to the next
    # each one only once
    routes = dict()

    for indi in my_paths:
        previous = me
        for ancestor in my_paths[indi]:
            route = str(previous) + ' -> ' + str(ancestor)
            routes[route] = ancestor
            previous = ancestor

    for indi in matches:
        if matches[indi]['path']:
           previous = indi
           for ancestor in matches[indi]['path']:
               route = str(previous) + ' -> ' + str(ancestor)
               routes[route] = ancestor
               previous = ancestor

    # count the number of connections into each family
    # so that the multiply connected can be coloured
    counts = dict()
    for route in routes:
        ancestor = routes[route]
        if ancestor not in counts:
           counts[ancestor] = 0
        counts[ancestor] += 1

    # assign the same color to the connection lines for the families
    # with multiple connections
    # and
    # loop through the colors to give a different color as each family matches
    ancestor_color = dict()
    n_colors = len( line_colors )
    c = n_colors + 1
    for ancestor in counts:
        if counts[ancestor] >= n_to_color:
           c = c + 1
           if c >= n_colors:
              c = 0
           ancestor_color[ancestor] = line_colors[c]

    # output the routes
    for route in routes:
        ancestor = routes[route]
        extra = ''
        if ancestor in ancestor_color:
           extra = ' [color=' + ancestor_color[ancestor] + ']'
        print( route + extra + ';' )

# these are keys into the parsed sections of the returned data structure
i_key = readgedcom.PARSED_INDI
f_key = readgedcom.PARSED_FAM

data = readgedcom.read_file( sys.argv[1] )

# people which do have the dna event
matched = dict()

# the id of the base dna match person
me = None

for indi in data[i_key]:
    result = check_for_dna_event( data[i_key][indi] )
    if result[0]:
       matched[indi] = dict()
       if result[1].lower().startswith( 'me,' ):
          matched[indi]['note'] = 'me'
          me = indi
       else:
          matched[indi]['note'] = extract_dna_cm( result[1] ) + ' cM'

if not me:
   print( 'Didnt find base person', file=sys.stderr )
   sys.exit()


my_ancestor_families = ancestor_families_of( me, data )

# how many generations do I have
max_gen = max( my_ancestor_families.values() )

# For each of the dna matched people,
# find the youngest ancestor which matches with me.
#
# Both people exist in the same tree so there must be a similar ancestor
# unless the dna match is noise. In this case the shared ancestor will be None.
#
# Findind shared ancestor person rather than shared ancestor family
# in order to skip half-cousins. Then in the display show only the people
# rather than families.

for indi in matched:

    found_match = None
    found_gen = max_gen + 1

    if indi != me:
       ancestor_families = ancestor_families_of( indi, data )

       for ancestor_fam in ancestor_families:
           if ancestor_fam in my_ancestor_families:
              if my_ancestor_families[ancestor_fam] < found_gen:
                 found_gen = my_ancestor_families[ancestor_fam]
                 found_match = ancestor_fam

    # the closest shared family
    matched[indi]['shared'] = found_match


# similar shared ancestor families
shared = dict()

for indi in matched:
    ancestor_fam = matched[indi]['shared']
    matched[indi]['path'] = None
    if ancestor_fam:
       if ancestor_fam not in shared:
          shared[ancestor_fam] = []
       shared[ancestor_fam].append( indi )
       family_path = find_ancestor_path( indi, ancestor_fam, data[i_key], data[f_key], [] )
       if family_path[0]:
          matched[indi]['path'] = family_path[1]
       else:
          matched[indi]['path'] = []


# find my own path to each of those shared ancestors
my_paths = dict()

for ancestor_fam in shared:
    family_path = find_ancestor_path( me, ancestor_fam, data[i_key], data[f_key], [] )
    if family_path[0]:
       my_paths[ancestor_fam] = family_path[1]

# output to stdout

begin_dot()

dot_labels( data[i_key], data[f_key], matched, my_paths )
dot_connect( matched, me, my_paths )

end_dot()
