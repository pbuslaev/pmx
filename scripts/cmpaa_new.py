import sys, os
from pmx import *
from pmx.ffparser import RTPParser, NBParser
from pmx.rotamer import _aa_chi
from pmx.parser import kickOutComments, readSection, parseList
import tempfile

standard_pair_list = [
    ('N','N'),
    ('H','H'),
    ('CA','CA'),
    ('C','C'),
    ('O','O'),
    ('HA','HA'),
    ('CB','CB'),
    ('1HB','1HB'),
    ('2HB','2HB'),
    ('CG','CG')
    ]

standard_pair_list_charmm = [
    ('N','N'),
    ('HN','HN'),
    ('CA','CA'),
    ('C','C'),
    ('O','O'),
    ('HA','HA'),
    ('CB','CB'),
    ('1HB','1HB'),
    ('2HB','2HB'),
    ('CG','CG')
    ]

standard_pair_listB = [
    ('N','N'),
    ('H','H'),
    ('CA','CA'),
    ('C','C'),
    ('O','O'),
    ('HA','HA'),
    ('CB','CB'),
    ('1HB','1HB'),
    ('2HB','2HB'),
    ('CG','CG')
    ]

standard_pair_listC = [
    ('N','N'),
    ('H','H'),
    ('CA','CA'),
    ('C','C'),
    ('O','O'),
    ('HA','HA'),
    ('CB','CB'),
    ('1HB','1HB'),
    ('2HB','2HB'),
    ('CG','CG')
    ]

standard_pair_listD = [
    ('N','N'),
    ('H','H'),
    ('CA','CA'),
    ('C','C'),
    ('O','O'),
    ('HA','HA'),
    ('CB','CB'),
    ('1HB','1HB'),
    ('2HB','2HB'),
    ('CG','CG')
    ]
    
use_standard_pair_list = {
    'PHE': [ 'TRP','HIP','HID','HIE','HSP','HSD','HSE','HIS1','HISH','HISE'],
    'TYR': [ 'TRP','HIP','HID','HIE','HSP','HSD','HSE','HIS1','HISH','HISE'],
    'TRP': [ 'PHE','TYR','HIP','HID','HSE','HSP','HSD','HSE','HIS1','HISH','HISE','HIE'],
    'HID': [ 'PHE','TYR','TRP'], #[ 'PHE','TYR','HIP','TRP','HIE'],
    'HIE': [ 'PHE','TYR','TRP'], #[ 'PHE','TYR','HIP','HID','TRP'],
    'HIP': [ 'PHE','TYR','TRP'], #,'HID','HIE'],
    'HSD': [ 'PHE','TYR','TRP'], #[ 'PHE','TYR','HIP','TRP','HIE'],
    'HSE': [ 'PHE','TYR','TRP'], #[ 'PHE','TYR','HIP','HID','TRP'],
    'HSP': [ 'PHE','TYR','TRP'], #,'HID','HIE'],
    'HIS1': [ 'TRP','PHE','TYR','HIP','HID','HIE','HISH','HISE'],
    'HISE': [ 'TRP','PHE','TYR','HIP','HID','HIE','HISH','HIS1'],
    'HISH': [ 'TRP','PHE','TYR','HIP','HID','HIE','HIS1','HISE']
    }

merge_by_name_list = {
    'PHE':['TYR'],
    'TYR':['PHE'],
    'HID':['HIP','HIE'],
    'HIE':['HIP','HID'],
    'HIP':['HID','HIE'],
    'HSD':['HSP','HSE'],
    'HSE':['HSP','HSD'],
    'HSP':['HSD','HSE'],
    'HIS1':['HISE','HISH'],
    'HISE':['HIS1','HISH'],
    'HISH':['HIS1','HISE']
}
    

mol_branch = {
    'ILE':2,
    'VAL':2,
    'LEU':3,
    'GLN':3,
    'GLU':3,
    'GLUH':3,
    'ASP':2,
    'ASN':2,
    'PHE':2,
    'TYR':2,
    'TRP':2,
    'HIS':2,
    'HIS1':2,
    'HISE':2,
    'HISH':2,
    'THR':2,
    'ALA':5,
    'SER':5,
    'GLY':5,
    'CYS':5,
    'MET':5,
    'ARG':5,
    'LYS':5,
    'LYN':5,
    }

def tag(atom):
    s = '%s|%s|%s|%s' %( atom.resname, atom.name, atom.atomtype, atom.atype)
    return '%-20s' % s

def align_sidechains(r1, r2):
    #MS: if you add new force field, check pmx/molecule.py, make sure res is
    #MS: correctly set into get_real_resname 
    for i in range(r1.nchi()):
        phi = r1.get_chi(i+1, degree = True)
        r2.set_chi(i+1,phi)

def assign_rtp_entries( mol, rtp):
    entr = rtp[mol.resname]
    neigh=[]
    # atoms
    for atom_entry in entr['atoms']:
        atom_name = atom_entry[0]
        atom_type = atom_entry[1]
        atom_q    = atom_entry[2]
        atom_cgnr = atom_entry[3]
        atom = mol.fetch( atom_name )[0]
        atom.atomtype = atom_type
        atom.q = atom_q
        atom.cgnr = atom_cgnr
    # bonds
    for a1, a2 in entr['bonds']:
	#MS charmm uses next residue in bonds (+), amber pervious (-)
	#MS also write rtp is affected now, since normally -C N is added
	#MS charmm used C +N, problem is that you run into trouble on the
	#MS termini
	bmin=not '-' in a1 and not '-' in a2
	bplus=not '+' in a1 and not '+' in a2
        if bmin and bplus:
            atom1, atom2 = mol.fetchm( [a1, a2] )
            atom1.bonds.append( atom2 )
            atom2.bonds.append( atom1 )
	else :
	    neigh.append([a1,a2])
    return neigh
        

def assign_branch(mol):
    for atom in mol.atoms:
        if atom.long_name[-1] == ' ':
            atom.branch = 0
        elif atom.long_name[-1] == '1':
            atom.branch = 1
        else:
            atom.branch = 2
        
def get_atoms_by_order(mol,order):
    res = []
    for atom in mol.atoms:
        if atom.order == order:
            res.append(atom)
    return res

def get_atoms_by_order_and_branch( mol, order, branch, merged_atoms ):
    res = []
    for atom in mol.atoms:
        if atom.order == order and atom not in merged_atoms:
            if atom.branch in [0,branch] or atom.branch < mol_branch[mol.real_resname] + 1:
                res.append(atom)
    return res
    

def last_atom_is_morphed( atom, merged_list ):
    for at in atom.bonds:
        if at.order < atom.order and at in merged_list:
            return True
    return False

def cmp_mol2_types( type1, type2 ):
    if type1 == type2 : return True
    if type1 == 'H' or type2 == 'H': return True
    tp1_ext = type1.split('.')[1]
    tp2_ext = type2.split('.')[1]
    if tp1_ext in ['2','3'] and \
       tp2_ext in ['2','3']:
        return False
    elif tp1_ext in ['am','co2'] and \
         tp2_ext in ['am','co2']:
        return True
    elif type1 in ['O.2','O.co2'] and \
         type2 in ['O.2','O.co2']:
        return True
    elif (type1[0] == 'S' and type2[0] != 'S') or \
         (type1[0] != 'S' and type2[0] == 'S'):
        return False
    else:
        return False
#        print type1, type2, '????'
#        sys.exit(1)
        
        
def find_closest_atom( atom1, atom_list, merged_atoms ):
    min_d = .55
    idx = 99
    for i, atom in enumerate(atom_list):
        if atom not in merged_atoms:
            d = atom1 - atom
            if d < min_d:
                min_d = d
                idx = i
    if idx != 99:
        return atom_list[idx], min_d
    else: return None, None

def make_predefined_pairs( mol1, mol2, pair_list ):
    # make main chain + cb pairs
    print 'Making atom pairs.........'
    atom_pairs = []
    merged_atoms1 = []
    merged_atoms2 = []
    for name1, name2 in pair_list:
        at1 = mol1.fetch( name1 )[0]
        at2 = mol2.fetch( name2 )[0]
        at1.atomtypeB = at2.atomtype
        at1.qB = at2.q
        at1.mB = at2.m
        at1.nameB = at2.name
        merged_atoms1.append( at1 )
        merged_atoms2.append( at2 )
        atom_pairs.append( [at1, at2] )
##         if atom.atomtypeB.startswith('DUM'):
##             atom.nameB = atom.name+'.gone'
    dummies = mol2.fetch_atoms( map( lambda a: a.name, merged_atoms1), inv = True )
    return atom_pairs, dummies

def merge_by_names( mol1, mol2 ):
    print 'Making atom pairs.........'
    atom_pairs = []
    merged_atoms1 = []
    merged_atoms2 = []
    for at1 in mol1.atoms:
        try:
            at2 = mol2.fetch( at1.name )[0]
            at1.atomtypeB = at2.atomtype
            at1.qB = at2.q
            at1.mB = at2.m
            at1.nameB = at2.name
            merged_atoms1.append( at1 )
            merged_atoms2.append( at2 )
            atom_pairs.append( [at1, at2] )
        except:
            pass
##         if atom.atomtypeB.startswith('DUM'):
##             atom.nameB = atom.name+'.gone'
    dummies = mol2.fetch_atoms( map( lambda a: a.name, merged_atoms1), inv = True )
    return atom_pairs, dummies

    

def make_pairs( mol1, mol2,bCharmm ):
    # make main chain + cb pairs
    print 'Making atom pairs.........'
    mol1.batoms = []
    merged_atoms1 = []
    merged_atoms2 = []
    atom_pairs = []
    if bCharmm :
        mc_list = ['N','CA','C','O','HN','HA','CB']
        gly_mc_list = ['N','CA','C','O','HN','1HA','2HA'] 
    else :
        mc_list = ['N','CA','C','O','H','HA','CB']
        gly_mc_list = ['N','CA','C','O','H','1HA','2HA'] 

    if mol1.resname == 'GLY':
        atoms1 = mol1.fetchm( gly_mc_list )
    else:
        atoms1 = mol1.fetchm( mc_list )
    if mol2.resname == 'GLY':
        atoms2 = mol2.fetchm( gly_mc_list )
    else:
        atoms2 = mol2.fetchm( mc_list )

    for at1, at2 in zip( atoms1, atoms2 ):
        at1.atomtypeB = at2.atomtype
        at1.qB = at2.q
        at1.mB = at2.m
        at1.nameB = at2.name
        mol1.batoms.append( at2 )
        merged_atoms1.append( at1 )
        merged_atoms2.append( at2 )
        atom_pairs.append( [at1, at2] )
    # now go for the rest of the side chain


    for k in [1,2]:
        print '-- Searching branch', k
        done_branch = False
        for i in range( 2, 8 ):
            if done_branch: break
            print '-- Searching order', i

            atoms1 = get_atoms_by_order_and_branch( mol1, i, k, merged_atoms1 )
            atoms2 = get_atoms_by_order_and_branch( mol2, i, k, merged_atoms2 )
            for at1 in atoms1:
                if last_atom_is_morphed( at1, merged_atoms1 ):
                    print '-- Checking atom...', at1.name
                    candidates = []
                    for at2 in atoms2:
                        if cmp_mol2_types( at1.atype, at2.atype):
                            candidates.append( at2 )
                    aa, d = find_closest_atom( at1, candidates, merged_atoms2 )
                    if aa:
                        merged_atoms2.append( aa )
                        merged_atoms1.append( at1 )
                        atom_pairs.append( [ at1, aa] )
                        print '--> Define atom pair: ', tag(at1), '- >', tag(aa),  '(d = %4.2f A)' % d
##                 else:
##                     print 'No partner found for atom ', at1.name
##                     print '-- done branch', k
##                     done_branch = True
##                     break # done with this branch
    for at1, at2 in atom_pairs:
        at1.atomtypeB = at2.atomtype
        at1.qB = at2.q
        at1.mB = at2.m
        at1.nameB = at2.name
        mol1.batoms.append( at2 )
##     for atom in mol1.atoms:
##         if atom.atomtypeB.startswith('DUM'):
##             atom.nameB+='.gone'
    # now make list of dummies
    dummies = []
    for atom in mol2.atoms:
        if atom not in merged_atoms2:
            dummies.append( atom )
    return atom_pairs, dummies


def check_double_atom_names( r ):
    for atom in r.atoms:
        alist = r.fetch_atoms( atom.name )
        if len(alist) != 1:
            alist = r.fetch_atoms( atom.name[:-1], wildcard = True )
            print 'Renaming atoms (%s)' % alist[0].name[:-1]
            start = 1
            for atom in alist:
                atom.name = atom.name[:3]+str(start)
                start+=1
            return False
    return True

def merge_molecules( r1, dummies ):
    
    for atom in dummies:
        new_atom = atom.copy()
        new_atom.atomtypeB = new_atom.atomtype
        new_atom.qB = new_atom.q
        new_atom.mB = new_atom.m
        new_atom.typeB = new_atom.type
        new_atom.atomtype = 'DUM_'+new_atom.atomtype
        new_atom.q = 0
        new_atom.nameB = new_atom.name
        if len(new_atom.name) == 4:
            new_atom.name = 'D'+new_atom.name[:3]
            if new_atom.name[1].isdigit():
                new_atom.name = new_atom.name[0]+new_atom.name[2:]+new_atom.name[1]
                
        else:
            new_atom.name = 'D'+atom.name
        r1.append( new_atom )


def make_bstate_dummies(r1):
    for atom in r1.atoms:
        if not hasattr(atom, "nameB"):
            atom.nameB = atom.name+'.gone'
            atom.atomtypeB = 'DUM_'+atom.atomtype
            atom.qB = 0
            atom.mB = atom.m
            
def make_transition_dics( atom_pairs, r1 ):
    abdic = {}
    badic = {}
    for a1, a2 in atom_pairs:
        abdic[a1.name] = a2.name
        badic[a2.name] = a1.name
    for atom in r1.atoms:
        if atom.name[0] == 'D':
            abdic[atom.name] = atom.name
            badic[atom.name] = atom.name
    return abdic, badic

def find_atom_by_nameB( r, name ):
    n = 0
    for atom in r1.atoms:
        if atom.nameB == name:
            return atom
    return None

def update_bond_lists(r1, badic):

    print 'Updating bond lists...........'
    for atom in r1.atoms:
        if atom.name[0] == 'D':
            print 'atom', atom.name
            print '  |  '
            new_list = []
            while atom.bonds:
                at = atom.bonds.pop(0)
                print atom.name, '->', at.name
                if badic.has_key(at.name):
                    aa = r1.fetch( badic[at.name] )[0]
                    new_list.append( aa )
                else:
                    aa = find_atom_by_nameB( r1, at.name )
                    if aa is not None:
                        new_list.append(aa)
                    else:
                        print 'Atom not found', at.name, at.nameB
                        sys.exit(1)
            atom.bonds = new_list
            for at in atom.bonds:
                if atom not in at.bonds:
                    at.bonds.append( atom )
                print  '----bond--->', at.name
            print

def improp_entries_match( lst1, lst2 ):
    for a1, a2 in zip(lst1, lst2):
        if a1.name != a2.name: return False
    return True

def generate_dihedral_entries( im1, im2, r, pairs ):
    print 'Updating dihedrals...........'
    new_ii = []
    done_i1 = []
    done_i2 = []
    # ILDN dihedrals
    for i1 in im1:
	#print '%s %s %s %s %s' % (i1[0].name,i1[1].name,i1[2].name,i1[3].name,i1[4])
        for i2 in im2:
            if improp_entries_match(i1[:4], i2[:4]) and (i2 not in done_i2):
                im_new = i1[:4]
                if i1[4] == '': 
		    im_new.append( 'default-A' )
                else: 
		    im_new.append( i1[4] )
                if i2[4] == '': 
		    im_new.append( 'default-B' )
                else: 
		    im_new.append( i2[4] )
                done_i1.append( i1 )
                done_i2.append( i2 )
                new_ii.append( im_new )
		break
    for i1 in im1:
        if i1 not in done_i1:
            im_new =  i1[:4]
            if i1[4] == '': 
                im_new.append( 'default-A' )
                if( ('gone' in i1[0].nameB) or ('gone' in i1[1].nameB) or ('gone' in i1[2].nameB) or ('gone' in i1[3].nameB) ):
                    im_new.append( 'default-A' )
                else:
                    im_new.append( 'undefined' )
            else:
		if ( ('gone' in i1[0].nameB) or ('gone' in i1[1].nameB) or ('gone' in i1[2].nameB) or ('gone' in i1[3].nameB) ):
  	            im_new.append( i1[4] )
                    im_new.append( i1[4] )
		else:
                    im_new.append( i1[4] )
                    if( 'torsion' in i1[4] ):	#ildn
                        foo = 'undefined_' + i1[4]
                        im_new.append( foo )
                    elif( 'dih_' in i1[4] ):	#opls
                        foo = 'undefined_' + i1[4]
                        im_new.append( foo )
                    else:
                        im_new.append( 'undefined' )
            new_ii.append( im_new )
    for i2 in im2:
        if i2 not in done_i2:
            im_new =  i2[:4] 
            if i2[4] == '': 
                if( (i2[0].name.startswith('D')) or (i2[1].name.startswith('D')) or (i2[2].name.startswith('D')) or (i2[3].name.startswith('D')) ):
                    im_new.append( 'default-B' )
                else:
                    im_new.append( 'undefined' )
		im_new.append( 'default-B' )
            else: 
                if ( (i2[0].name.startswith('D')) or (i2[1].name.startswith('D')) or (i2[2].name.startswith('D')) or (i2[3].name.startswith('D')) ):
                    im_new.append( i2[4] )
                    im_new.append( i2[4] )
                else:
                    if( 'torsion' in i2[4] ):	#ildn
			foo = 'undefined_' + i2[4]
			im_new.append( foo )
                    if( 'dih_' in i2[4] ):   #opls
                        foo = 'undefined_' + i2[4]
                        im_new.append( foo )
		    else:
		        im_new.append( 'undefined' )
                    im_new.append( i2[4] )
            new_ii.append( im_new )
    
    return new_ii

def generate_improp_entries( im1, im2, r ):
    print 'Updating impropers...........'
    
    new_ii = []
    done_i1 = []
    done_i2 = []
    # common impropers
    for i1 in im1:
        for i2 in im2:
            if improp_entries_match(i1[:4], i2[:4]):
		print 'alus %s' % i1[4]
                im_new = i1[:4]
                if i1[4] == '': 
		    im_new.append( 'default-A' )
		elif( i1[4] == '105.4' ): #star
		    im_new.append( 'default-star' )
                else: 
		    im_new.append( i1[4] )
                if i2[4] == '': 
		    im_new.append( 'default-B' )
                elif( i2[4] == '105.4' ): #star
                    im_new.append( 'default-star' )
                else: 
		    im_new.append( i2[4] )
                done_i1.append( i1 )
                done_i2.append( i2 )
                new_ii.append( im_new )
    for i1 in im1:
        if i1 not in done_i1:
            im_new =  i1[:4] 
            if i1[4] == '': 
	        im_new.append( 'default-A' )
		if( ('gone' in i1[0].nameB) or ('gone' in i1[1].nameB) or ('gone' in i1[2].nameB) or ('gone' in i1[3].nameB) ):
	            im_new.append( 'default-A' )
		else:
		    im_new.append( 'undefined' )
            elif( i1[4] == '105.4' ): #star
                im_new.append( 'default-star' )
                im_new.append( 'undefined' )
            else: 
		im_new.append( i1[4] )
                if( ('gone' in i1[0].nameB) or ('gone' in i1[1].nameB) or ('gone' in i1[2].nameB) or ('gone' in i1[3].nameB) ):
                    im_new.append( i1[4] )
                else:
                    im_new.append( 'undefined' )
            new_ii.append( im_new )
    for i2 in im2:
        if i2 not in done_i2:
            im_new =  i2[:4] #[ find_atom_by_nameB(r, n) for n in i2[:4] ] 
#            im_new.append( 'default-B' )
            if i2[4] == '': 
                if( (i2[0].name.startswith('D')) or (i2[1].name.startswith('D')) or (i2[2].name.startswith('D')) or (i2[3].name.startswith('D')) ):
                    im_new.append( 'default-B' )
                else:
                    im_new.append( 'undefined' )
	        im_new.append( 'default-B' )
            elif( i2[4] == '105.4' ): #star
                im_new.append( 'undefined' )
                im_new.append( 'default-star' )
            else:
                if( (i2[0].name.startswith('D')) or (i2[1].name.startswith('D')) or (i2[2].name.startswith('D')) or (i2[3].name.startswith('D')) ):
                    im_new.append( i2[4] )
                else:
                    im_new.append( 'undefined' )
		im_new.append( i2[4] )
            new_ii.append( im_new )
##     for ii in new_ii:
##         print '--->', ' '.join(ii)
##     print
    return new_ii

def write_rtp( fp, r, ii_list, dihi_list,neigh_bonds,cmap):
    print >>fp,'\n[ %s ] ; %s -> %s\n' % (r.resname, r.resnA, r.resnB)
    print >>fp,' [ atoms ]'
    cgnr = 1
    for atom in r.atoms:
        print >>fp, "%6s   %-15s  %8.5f  %d" % (atom.name, atom.atomtype, atom.q, cgnr)
        cgnr+=1
    print >>fp,'\n [ bonds ]'
    for atom in r.atoms:
        for at  in atom.bonds:
            if atom.id < at.id:
                print >>fp, "%6s  %6s ; (%6s  %6s)" % ( atom.name, at.name, atom.nameB, at.nameB )
    #MS here there will have to be a check for FF, since for charmm we need to add C N
    #MSsave those bonds with previous and next residue as a seperate entry
    for i in neigh_bonds :
        print >>fp, "%6s  %6s  " % (i[0],i[1])

    print >>fp,'\n [ impropers ]'
    for ii in ii_list:
        if not ii[4].startswith('default'):
            print >>fp, "%6s  %6s  %6s  %6s  %-25s" % ( ii[0].name, ii[1].name, ii[2].name, ii[3].name, ii[4])
        else:
            print >>fp, "%6s  %6s  %6s  %6s " % ( ii[0].name, ii[1].name, ii[2].name, ii[3].name)

    print >>fp,'\n [ dihedrals ]'
    for ii in dihi_list:
        if not ii[4].startswith('default'):
            print >>fp, "%6s  %6s  %6s  %6s  %-25s" % ( ii[0].name, ii[1].name, ii[2].name, ii[3].name, ii[4])
        else:
            print >>fp, "%6s  %6s  %6s  %6s " % ( ii[0].name, ii[1].name, ii[2].name, ii[3].name)
    if cmap :
        print >>fp,'\n [ cmap ]'
    for i in cmap:
        print >>fp, "%s  " % (i)

def write_mtp( fp, r, ii_list, rotations, dihi_list ):
    print >>fp,'\n[ %s ] ; %s -> %s\n' % (r.resname, r.resnA, r.resnB)
    print >>fp,'\n [ morphes ]'
    for atom in r.atoms:
        print >>fp, "%6s %10s -> %6s %10s" % ( atom.name, atom.atomtype, atom.nameB, atom.atomtypeB )
    print >>fp,'\n [ atoms ]'
    cgnr = 1
    for atom in r.atoms:
        ext = ' ; '
        if atom.atomtype != atom.atomtypeB: ext+= ' types != '
        else: ext+= ' types == '
        if atom.q != atom.qB: ext+= '| charge != '
        else: ext+= '| charge == '

        print >>fp ,"%8s %10s %10.6f %6d %10.6f %10s %10.6f %10.6f  %-10s" % \
              ( atom.name, atom.atomtype, atom.q, cgnr, atom.m, atom.atomtypeB, atom.qB, atom.mB, ext )
    print >>fp,'\n [ coords ]'
    for atom in r.atoms:
        print >>fp,"%8.3f %8.3f %8.3f" % (atom.x[0], atom.x[1], atom.x[2])

    print >>fp,'\n [ impropers ]'
    for ii in ii_list:
        print >>fp," %6s %6s %6s %6s     %-25s %-25s  " % \
              ( ii[0].name, ii[1].name, ii[2].name, ii[3].name, ii[4], ii[5] )
    print

    print >>fp,'\n [ dihedrals ]'
    for ii in dihi_list:
        print >>fp," %6s %6s %6s %6s     %-25s %-25s  " % \
              ( ii[0].name, ii[1].name, ii[2].name, ii[3].name, ii[4], ii[5] )
    print

    if rotations:
        print >>fp, '\n [ rotations ]'
        for rot in rotations:
            print >>fp, '  %s-%s %s' % (rot[0].name, rot[1].name, ' '.join( map(lambda a: a.name, rot[2:]) ) )
        print >>fp

def primitive_check( atom, rot_atom ):
    if atom in rot_atom.bonds: return True
    else: return False
    
def find_higher_atoms( rot_atom, r, order, branch ):
    res = []
    for atom in r.atoms:
        if atom.order >= order and \
           (atom.branch == branch or branch == 0):
            if atom.order ==  rot_atom.order+1:
                if primitive_check( atom, rot_atom ):
                    res.append( atom )
            else:
                res.append( atom )
                
    return res

def make_rotations( r ):
    rotations = []
    for chi in range(1, r.nchi() + 1):
        rot_list = []
        dih_atoms = r.fetchm( _aa_chi[r.real_resname][chi][0] )
        rot_atoms = [ dih_atoms[1], dih_atoms[2] ]
        atom1 = rot_atoms[0]
        atom2 = rot_atoms[1]
        rot_list.append( atom1 )
        rot_list.append( atom2 )
        oo = atom2.order
        bb = atom2.branch
        atoms_to_rotate = []
        atoms_to_rotate =  find_higher_atoms(atom2,  r, oo+1, bb ) 
        for atom in atoms_to_rotate:
            rot_list.append( atom )
        rotations.append( rot_list )
    return rotations

def parse_ffnonbonded_charmm(ffnonbonded,f):
    ifile=open(ffnonbonded,'r')
    lines=ifile.readlines()
    #now clean the heavy atom entries from file and write it to temp file
    bAdd=True
    for line in lines:
        if line.strip()=='#ifdef HEAVY_H' :
	    bAdd=False
	if bAdd and line[0]!='#':
	    f.write(line)
	if line.strip()=='#else' :
	    bAdd=True
	if line.strip()=='#endif' :
	    bAdd=True

def assign_mass(r1, r2,ffnonbonded,bCharmm,ff):
    #MS open ffnonbonded, remove HEAVY_H, pass it to NBParser 
    if bCharmm : 
        f=tempfile.NamedTemporaryFile(delete=False)
	parse_ffnonbonded_charmm(ffnonbonded,f)
	print f.name
        NBParams = NBParser(f.name,'new',ff)
	f.close()
    else : 
        NBParams = NBParser(ffnonbonded,'new',ff)
    for atom in r1.atoms+r2.atoms:
#        print atom.atomtype, atom.name
        atom.m =  NBParams.atomtypes[atom.atomtype]['mass']
        
def rename_to_gmx( r ):
    for atom in r1.atoms:
        if atom.name[0].isdigit():
            atom.name = atom.name[1:]+atom.name[0]
        if atom.nameB[0].isdigit():
            atom.nameB = atom.nameB[1:]+atom.nameB[0]
        if atom.name[0] == 'D' and atom.name[1].isdigit():
            atom.name = atom.name[0]+atom.name[2:]+atom.name[1]
        if atom.nameB[0] == 'D' and atom.nameB[1].isdigit():
            atom.nameB = atom.nameB[0]+atom.nameB[2:]+atom.nameB[1]
    res = False
    while not res:
        res = check_double_atom_names( r )
        
def improps_as_atoms( im, r, use_b = False):
    im_new = []
    for ii in im:
        atom_names = ii[:4]
        new_ii = []
        for name in atom_names:
            if name[0] in ['+','-']:
                a = Atom( name = name )
            else:
                if use_b:
                    for atom in r.atoms:
                        if atom.nameB == name:
                            a = atom
                else:
                    a = r.fetch( name )[0]
            new_ii.append( a )
        new_ii.extend( ii[4:] )
        im_new.append( new_ii )
    return im_new


def read_nbitp(fn):
    l = open(fn,'r').readlines()
    l = kickOutComments(l,';')
    l = readSection(l,'[ atomtypes ]','[')
    l = parseList('ssiffsff',l)
    dic = {}
    for entry in l:
        dic[entry[0]]=entry[1:]
    return dic

def write_atp_fnb(fn_atp,fn_nb,r,ff):
    types=[]
    if os.path.isfile(fn_atp) : 
        ifile=open(fn_atp,'r')
	for line in ifile:
	    sp=line.split()
	    types.append(sp[0])
	ifile.close()
    if os.path.isfile(fn_atp) :
        ofile=open(fn_atp,'a')
    else :
        ofile=open(fn_atp,'w')

    for atom in r.atoms:
        if atom.atomtype[0:3]=='DUM':
	    if atom.atomtype not in types:
                ofile.write("%-6s  %10.6f\n" % (atom.atomtype,atom.m))
		types.append(atom.atomtype)
        if atom.atomtypeB[0:3]=='DUM':
	    if atom.atomtypeB not in types:
                ofile.write("%-6s  %10.6f\n" % (atom.atomtypeB,atom.mB))
		types.append(atom.atomtypeB)
    ofile.close()

    types=[]
    if os.path.isfile(fn_nb) : 
        ifile=open(fn_nb,'r')
	for line in ifile:
	    sp=line.split()
	    types.append(sp[0])
	ifile.close()
    if os.path.isfile(fn_nb) :
        ofile=open(fn_nb,'a')
    else :
        ofile=open(fn_nb,'w')
    print types

    # for opls need to extract the atom name
    if( 'opls' in ff):
	dum_real_name = read_nbitp(cmdl['-ffnb'])

    for atom in r.atoms:
        if atom.atomtype[0:3]=='DUM':
	    if atom.atomtype not in types:
		if( 'opls' in ff):
		    foo = dum_real_name['opls_'+atom.atomtype.split('_')[2]]
                    ofile.write("%-13s\t\t%3s\t0\t%4.2f\t   0.0000  A   0.00000e+00 0.00000e+00\n" \
		     % (atom.atomtype,foo[0],atom.m))
		else:
                    ofile.write("%-10s\t0\t%4.2f\t   0.0000  A   0.00000e+00 0.00000e+00\n" \
		     % (atom.atomtype,atom.m))
		types.append(atom.atomtype)
        if atom.atomtypeB[0:3]=='DUM':
	    if atom.atomtypeB not in types:
		if( 'opls' in ff):
                    foo = dum_real_name['opls_'+atom.atomtypeB.split('_')[2]]
                    ofile.write("%-13s\t\t%3s\t0\t%4.2f\t   0.0000  A   0.00000e+00 0.00000e+00\n" \
                     % (atom.atomtypeB,foo[0],atom.mB))
		else:
                    ofile.write("%-10s\t0\t%4.2f\t   0.0000  A   0.00000e+00 0.00000e+00\n" \
		     % (atom.atomtypeB,atom.mB))
		types.append(atom.atomtypeB)
    ofile.close()
	        
#    lines=fatp.readlines()
#    for 
#    types=[]
#    for line in lines:
#        
#    #write output for atomtypes
#    #write output for ffnonbonded.itp
#    fnb.write("%-10s\t0\t%4.2f\t   0.0000  A   0.00000e+00 0.00000e+00\n" \
#		     % (atom.atomtypeB,atom.mB))
#
#MS charmm uses HN instead of H for backbone H on N
def rename_atoms_charmm(m):
    for atom in m.atoms:
        if atom.name=='H' :
	    atom.name='HN'
        if atom.name=='HG' and atom.resname=='CYS' :
	    atom.name='1HG'
        if atom.name=='HG' and atom.resname=='SER' :
	    atom.name='1HG'

def rename_res_charmm(m):
    rename={'HIE':'HSE','HID':'HSD','HIP':'HSP','ASH':'ASPP','GLH':'GLUP','LYN':'LSN'}
    for res in m.residues:
        if rename.has_key(res.resname):
	    res.resname=rename[res.resname]
	    for atom in res.atoms:
	        atom.resname=res.resname

   
files= [
   FileOption("-pdb1", "r",["pdb"],"a1.pdb",""),
   FileOption("-pdb2", "r",["pdb"],"a2.pdb",""),
   FileOption("-opdb1", "w",["pdb"],"r1.pdb",""),
   FileOption("-opdb2", "w",["pdb"],"r2.pdb",""),
   FileOption("-ff", "r",["rtp"],"aminoacids.rtp",""),
   FileOption("-ffnb", "r",["itp"],"ffnonbonded.rtp",""),
   FileOption("-fatp", "w",["atp"],"types.atp",""),
   FileOption("-fnb", "w",["itp"],"fnb.itp",""),
]

options=[
   Option( "-ft", "string", "charmm" , "force field type (charmm, amber99sb, amber99sb*-ildn, oplsaa"),
   Option( "-align", "bool", True, "align side chains"),
	]
help_text = ("cmpaa.py reads two pdb files aligned on the backbone togheter with an rtp file.",
		"This is used to generate a hybrid residue.\n")

#options=[Option("-ff", "string", False ,"aminoacids.rtp")]
cmdl = Commandline( sys.argv, options = options, 
		     fileoptions = files,
                     program_desc = help_text,
                     check_for_existing_files = False )
if cmdl['-ft']=="charmm":
    bCharmm=True
else :
    bCharmm=False
align = cmdl['-align']

rtpfile=cmdl['-ff']
m1 = Model(cmdl['-pdb1'])
m2 = Model(cmdl['-pdb2'])
nm1=cmdl['-pdb1']
nm2=cmdl['-pdb2']
aa1 = nm1.split('.')[0].split('_')[0]
aa2 = nm2.split('.')[0].split('_')[0]

rr_name = aa1+'2'+aa2

m1.get_symbol()
m2.get_symbol()
m1.get_order()
m2.get_order()
m1.rename_atoms()
m2.rename_atoms()

if bCharmm:
    rename_atoms_charmm(m1)
    rename_atoms_charmm(m2)
    rename_res_charmm(m1)
    rename_res_charmm(m2)

r1 = m1.residues[0]
r2 = m2.residues[0]

r1.get_mol2_types()
r2.get_mol2_types()
r1.get_real_resname()
r2.get_real_resname()
if(align):
    align_sidechains(r1,r2)

r1.resnA = r1.resname[0]+r1.resname[1:].lower()
r1.resnB = r2.resname[0]+r2.resname[1:].lower()

r1.write(cmdl['-opdb1'])
r2.write(cmdl['-opdb2'])

#rtp = RTPParser('amber99sb-star-ildn.ff/aminoacids.rtp')
rtp = RTPParser(rtpfile)
bond_neigh=assign_rtp_entries( r1, rtp )
assign_rtp_entries( r2, rtp )
assign_mass( r1, r2 ,cmdl['-ffnb'],bCharmm,cmdl['-ft'])


assign_branch( r1 )
assign_branch( r2 )

if use_standard_pair_list.has_key( r1.resname ) and \
   r2.resname in use_standard_pair_list[r1.resname]:
    if bCharmm :
        atom_pairs, dummies = make_predefined_pairs( r1, r2, standard_pair_list_charmm)
    else :
        if(len(r1.resname)==3 and len(r2.resname)==3):
            atom_pairs, dummies = make_predefined_pairs( r1, r2, standard_pair_list)
        elif(len(r1.resname)==4 and len(r2.resname)==3):
            atom_pairs, dummies = make_predefined_pairs( r1, r2, standard_pair_listC)
        elif(len(r1.resname)==3 and len(r2.resname)==4):
            atom_pairs, dummies = make_predefined_pairs( r1, r2, standard_pair_listB)
        elif(len(r1.resname)==4 and len(r2.resname)==4):
            atom_pairs, dummies = make_predefined_pairs( r1, r2, standard_pair_listD)

elif merge_by_name_list.has_key( r1.resname ) and r2.resname in merge_by_name_list[r1.resname]: 
    atom_pairs, dummies = merge_by_names( r1, r2 ) #make_predefined_pairs( r1, r2, standard_pair_list) 
else:    
    atom_pairs, dummies = make_pairs( r1, r2,bCharmm )

merge_molecules( r1, dummies )
make_bstate_dummies( r1 )

write_atp_fnb(cmdl["-fatp"],cmdl["-fnb"],r1,cmdl['-ft'])
abdic, badic = make_transition_dics( atom_pairs, r1)

update_bond_lists( r1, badic )

# VG #
# CMAP for charmm #

# VG #
# dihedrals are necessary for ILDN #
dih_1 = rtp[r1.resname]['diheds']
dih_2 = rtp[r2.resname]['diheds']

dih1 = improps_as_atoms( dih_1, r1) #its alright, can use improper function
dih2 = improps_as_atoms( dih_2, r1, use_b = True)

# VG #
# here go impropers #
im_1 = rtp[r1.resname]['improps']
im_2 = rtp[r2.resname]['improps']

im1 = improps_as_atoms( im_1, r1)
im2 = improps_as_atoms( im_2, r1, use_b = True)
#for x in dih1:
#    print x
## print
## for x in im2:
##     print x

# cmap #
cmap=[]
if bCharmm :
    cmap=rtp[r1.resname]['cmap']

# dihedrals #
dihi_list = generate_dihedral_entries(dih1, dih2, r1, atom_pairs)

# impropers #
ii_list = generate_improp_entries(im1, im2, r1)

rot = make_rotations(r1)

r1.set_resname( rr_name )
rename_to_gmx( r1 )

rtp_out = open(rr_name+'.rtp','w')
write_rtp(rtp_out, r1,ii_list, dihi_list, bond_neigh,cmap)
r1.write(rr_name+'.pdb')
mtp_out = open(rr_name+'.mtp','w')

write_mtp(mtp_out, r1, ii_list, rot, dihi_list)     
