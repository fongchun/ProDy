# -*- coding: utf-8 -*-

"""This module defines functions for calculating different types of interactions 
in protein structure, between proteins or between protein and ligand.
The following interactions are available for protein interactions:
        (1) Hydrogen bonds
        (2) Salt Bridges
        (3) Repulsive Ionic Bonding 
        (4) Pi stacking interactions
        (5) Pi-cation interactions
        (6) Hydrophobic interactions

For protein-ligand interactions (3) is replaced by water bridges.
"""

__author__ = 'Karolina Mikulska-Ruminska'
__credits__ = ['James Krieger', 'Karolina Mikulska-Ruminska']
__email__ = ['karolamik@fizyka.umk.pl', 'jamesmkrieger@gmail.com']


import numpy as np
from numpy import *
from prody import LOGGER, SETTINGS
from prody.atomic import AtomGroup, Atom, Atomic, Selection, Select
from prody.atomic import flags
from prody.utilities import importLA, checkCoords
from prody.measure import calcDistance, calcAngle, calcCenter
from prody.measure.contacts import findNeighbors
from prody.proteins import writePDB, parsePDB
from collections import Counter

from prody.trajectory import TrajBase
from prody.ensemble import Ensemble

__all__ = ['calcHydrogenBonds', 'calcChHydrogenBonds', 'calcSaltBridges',
           'calcRepulsiveIonicBonding', 'calcPiStacking', 'calcPiCation',
           'calcHydrophobic', 'calcDisulfideBonds', 'calcMetalInteractions',
           'calcHydrogenBondsDCD', 'calcSaltBridgesDCD',
           'calcRepulsiveIonicBondingDCD', 'calcPiStackingDCD', 
           'calcPiCationDCD', 'calcHydrophobicDCD', 'calcDisulfideBondsDCD',
           'calcProteinInteractions', 'calcStatisticsInteractions',
           'compareInteractions', 
           'calcLigandInteractions', 'listLigandInteractions', 
           'showProteinInteractions_VMD', 'showLigandInteraction_VMD', 
           'addHydrogens', 'calcHydrogenBondsDCD',
           'Interactions', 'InteractionsDCD']


def cleanNumbers(listContacts):
    """Provide short list with indices and value of distance"""
    
    shortList = [ [int(str(i[0]).split()[-1].strip(')')), 
                           int(str(i[1]).split()[-1].strip(')')), 
                           str(i[0]).split()[1], 
                           str(i[1]).split()[1], 
                           float(i[2])] for i in listContacts ]    
    
    return shortList


def calcPlane(atoms):
    """Function provide parameters of a plane for aromatic rings (based on 3 points).
    Used in calcPiStacking()"""
    
    coordinates = atoms.getCoords()
    p1, p2, p3 = coordinates[:3] # 3 points will be enough to obtain the plane
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    x3, y3, z3 = p3    
    vec1 = p3 - p1 # These two vectors are in the plane
    vec2 = p2 - p1
    cp = np.cross(vec1, vec2) # the cross product is a vector normal to the plane
    a, b, c = cp
    d = np.dot(cp, p3) # This evaluates a * x3 + b * y3 + c * z3 which equals d
    
    return a,b,c,d


def calcAngleBetweenPlanes(a1, b1, c1, a2, b2, c2):  
    """Find angle between two planes"""
    import math 
          
    d = ( a1 * a2 + b1 * b2 + c1 * c2 ) 
    eq1 = math.sqrt( a1 * a1 + b1 * b1 + c1 * c1) 
    eq2 = math.sqrt( a2 * a2 + b2 * b2 + c2 * c2) 
    d = d / (eq1 * eq2) 
    AngleBetweenPlanes = math.degrees(math.acos(d)) 
    
    return AngleBetweenPlanes
    
    
def removeDuplicates(list_of_interactions):
    ls=[]
    newList = []
    for no, i in enumerate(list_of_interactions):
       i = sorted(list(array(i).astype(str)))
       if i not in ls:
           ls.append(i)
           newList.append(list_of_interactions[no])
    return newList


def selectionByKwargs(list_of_interactions, atoms, **kwargs):
    """Return interactions based on selection"""
    
    if 'selection' in kwargs:
        if 'selection2' in kwargs:
            ch1 = kwargs['selection'].split()[-1] 
            ch2 = kwargs['selection2'].split()[-1] 
            final = [i for i in list_of_interactions if (i[2] == ch1 and i[5] == ch2) or (i[5] == ch1 and i[2] == ch2)]
        else:
            p = atoms.select('same residue as protein within 10 of ('+kwargs['selection']+')')
            x = p.select(kwargs['selection']).getResnames()
            y = p.select(kwargs['selection']).getResnums()
            listOfselection = np.unique(list(map(lambda x, y: x + str(y), x, y)))
            final = [i for i in list_of_interactions if i[0] in listOfselection or i[3] in listOfselection]
    else:
        final = list_of_interactions
    return final


def addHydrogens(pdb, method='openbabel', pH=7.0):    
    """Function will add hydrogens to the protein and ligand structure using Openbabel [NO11]_
    or PDBFixer with OpenMM.
    
    :arg pdb: PDB file name
    :type pdb: str

    :arg method: Name of program which will be use to fix protein structure.
            Two alternative options are available: 'openbabel' and 'pdbfixer'.
            For either option additional software need to be installed:
            'openbabel': OpenBabel
            'pdbfixer': PDBFixer and OpenMM
            default is 'openbabel'
    :type method: str
    
    :arg pH: pH value applyed only for PDBfixer.
    :type pH: int, float
    
    Instalation of Openbabel:
    conda install -c conda-forge openbabel    

    Find more information here: https://anaconda.org/conda-forge/openbabel
                                https://github.com/openmm/pdbfixer
    Program will create new file in the same directory with 'addH_' prefix.
    
    .. [NO11] O'Boyle, N. M., Banck M., James C. A., Morley C., Vandermeersch T., Hutchison G. R. 
    Open Babel: An open chemical toolbox *Journal of cheminformatics* **2011** 3:1-14. """
    
    if method == 'openbabel':
        try:
            #import openbabel
            from openbabel import openbabel
            obconversion = openbabel.OBConversion()
            obconversion.SetInFormat("pdb")
            mol = openbabel.OBMol()
            obconversion.ReadFile(mol, pdb)
            mol.AddHydrogens()
            obconversion.WriteFile(mol, 'addH_'+pdb)
            LOGGER.info("Hydrogens were added to the structure. Structure {0} is saved in the local directry.".format('addH_'+pdb))
        except ImportError:
            raise ImportError("Install Openbabel to add hydrogens to the structure or use PDBFixer/OpenMM.")
            
    elif method == 'pdbfixer':
        try:
            from pdbfixer import PDBFixer
            try:
                import openmm
                from openmm.app import PDBFile
            except ImportError:
                from simtk.openmm.app import PDBFile
            
            fixer = PDBFixer(filename=pdb)
            fixer.findMissingResidues()
            fixer.removeHeterogens(True)
            fixer.findMissingAtoms()
            fixer.addMissingAtoms()
            fixer.addMissingHydrogens(pH)
            PDBFile.writeFile(fixer.topology, fixer.positions, open('addH_'+pdb, 'w'))
            LOGGER.info("Hydrogens were added to the structure. Structure {0} is saved in the local directry.".format('addH_'+pdb))

        except ImportError:
            raise ImportError('Install PDBFixer and OpenMM in order to fix the protein structure.')

    else:
        raise TypeError('Method should be openbabel or pdbfixer')
    
    
def calcHydrogenBonds(atoms, distA=3.0, angle=40, cutoff_dist=20, **kwargs):
    """Compute hydrogen bonds for proteins and other molecules.
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg distA: non-zero value, maximal distance between donor and acceptor.
    :type distA: int, float, default is 3.0
    
    :arg angle: non-zero value, maximal (180 - D-H-A angle) (donor, hydrogen, acceptor).
    :type angle: int, float, default is 40.
    
    :arg cutoff_dist: non-zero value, interactions will be found between atoms with index differences
        that are higher than cutoff_dist.
        default is 20 atoms.
    :type cutoff_dist: int

    Structure should contain hydrogens.
    If not they can be added using addHydrogens(pdb_name) function available in ProDy after Openbabel installation.
    `conda install -c conda-forge openbabel`
    
    Note that the angle which it is considering is 180-defined angle D-H-A (in a good agreement with VMD)
    Results can be displayed in VMD by using showVMDinteraction() """

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')
    
    donors = kwargs.get('donors', ['N', 'O', 'S', 'F'])
    acceptors = kwargs.get('acceptors', ['N', 'O', 'S', 'F'])
    
    if atoms.hydrogen == None or atoms.hydrogen.numAtoms() < 10:
        LOGGER.info("Provide structure with hydrogens or install Openbabel to add missing hydrogens using addHydrogens(pdb_name) first.")
    
    contacts = findNeighbors(atoms.heavy, distA)
    short_contacts = cleanNumbers(contacts)
    pairList = [] # list with Donor-Hydrogen-Acceptor(indices)-distance-Angle
    
    LOGGER.info('Calculating hydrogen bonds.')
    for nr_i,i in enumerate(short_contacts):
        # Removing those close contacts which are between neighbour atoms
        if i[1] - cutoff_dist < i[0] < i[1] + cutoff_dist:
            pass
        
        else:
            if (i[2][0] in donors and i[3][0] in acceptors) or (i[2][0] in acceptors and i[3][0] in donors): # First letter is checked
                listOfHydrogens1 = cleanNumbers(findNeighbors(atoms.hydrogen, 1.4, atoms.select('index '+str(i[0]))))
                listOfHydrogens2 = cleanNumbers(findNeighbors(atoms.hydrogen, 1.4, atoms.select('index '+str(i[1]))))
                AtomsForAngle = ['D','H','A', 'distance','angle']
                
                if not listOfHydrogens1:
                    for j in listOfHydrogens2:
                        AtomsForAngle = [j[1], j[0], i[0], i[-1], calcAngle(atoms.select('index '+str(j[1])), 
                                                                        atoms.select('index '+str(j[0])), 
                                                                        atoms.select('index '+str(i[0])))[0]]                                                                                   
                        pairList.append(AtomsForAngle)            
                
                elif not listOfHydrogens2:
                    for jj in listOfHydrogens1:
                        AtomsForAngle = [jj[1], jj[0], i[1], i[-1], calcAngle(atoms.select('index '+str(jj[1])), 
                                                                          atoms.select('index '+str(jj[0])), 
                                                                          atoms.select('index '+str(i[1])))[0]]
                        pairList.append(AtomsForAngle)            
       
                else:            
                    for j in listOfHydrogens2:
                        AtomsForAngle = [j[1], j[0], i[0], i[-1], calcAngle(atoms.select('index '+str(j[1])), 
                                                                            atoms.select('index '+str(j[0])), 
                                                                            atoms.select('index '+str(i[0])))[0]]                                                                                   
                        pairList.append(AtomsForAngle)
    
                    
                    for jj in listOfHydrogens1:
                        AtomsForAngle = [jj[1], jj[0], i[1], i[-1], calcAngle(atoms.select('index '+str(jj[1])), 
                                                                              atoms.select('index '+str(jj[0])), 
                                                                              atoms.select('index '+str(i[1])))[0]]
                        pairList.append(AtomsForAngle)
    
    HBs_list = []
    for k in pairList:
        if 180-angle < float(k[-1]) < 180 and float(k[-2]) < distA:
            aa_donor = atoms.getResnames()[k[0]]+str(atoms.getResnums()[k[0]])
            aa_donor_atom = atoms.getNames()[k[0]]+'_'+str(k[0])
            aa_donor_chain = atoms.getChids()[k[0]]
            aa_acceptor = atoms.getResnames()[k[2]]+str(atoms.getResnums()[k[2]])
            aa_acceptor_atom = atoms.getNames()[k[2]]+'_'+str(k[2])
            aa_acceptor_chain = atoms.getChids()[k[2]]
            
            HBs_list.append([str(aa_donor), str(aa_donor_atom), str(aa_donor_chain), str(aa_acceptor), str(aa_acceptor_atom), 
                             str(aa_acceptor_chain), np.round(float(k[-2]),2), np.round(180.0-float(k[-1]),2)])
    
    HBs_list = sorted(HBs_list, key=lambda x : x[-2])
    HBs_list_final = removeDuplicates(HBs_list)
    HBs_list_final2 = selectionByKwargs(HBs_list_final, atoms, **kwargs)
    
    LOGGER.info(("%26s   <---> %30s%12s%7s" % ('DONOR (res chid atom)','ACCEPTOR (res chid atom)','Distance','Angle')))
    for kk in HBs_list_final2:
        LOGGER.info("%10s%5s%14s  <---> %10s%5s%14s%8.1f%8.1f" % (kk[0], kk[2], kk[1], kk[3], kk[5], kk[4], kk[6], kk[7]))
                                
    LOGGER.info("Number of detected hydrogen bonds: {0}.".format(len(HBs_list_final2)))
                
    return HBs_list_final2   
    
    
def calcChHydrogenBonds(atoms, distA=3.0, angle=40, cutoff_dist=20, **kwargs):
    """Finds hydrogen bonds between different chains.
    See more details in calcHydrogenBonds().
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg distA: non-zero value, maximal distance between donor and acceptor.
    :type distA: int, float, default is 3.0.

    :arg angle: non-zero value, D-H-A angle (donor, hydrogen, acceptor).
    :type angle: int, float, default is 40.
    
    :arg cutoff_dist: non-zero value, interactions will be found between atoms with index differences
        that are higher than cutoff_dist.
        default is 20 atoms.
    :type cutoff_dist: int

    Structure should contain hydrogens.
    If not they can be added using addHydrogens(pdb_name) function available in ProDy after Openbabel installation.
    `conda install -c conda-forge openbabel`
    
    Note that the angle which it is considering is 180-defined angle D-H-A (in a good agreement with VMD)
    Results can be displayed in VMD. """

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    if len(np.unique(atoms.getChids())) > 1:
        HBS_calculations = calcHydrogenBonds(atoms, **kwargs)
    
        ChainsHBs = [ i for i in HBS_calculations if str(i[2]) != str(i[5]) ]
        if not ChainsHBs:
            ligand_name = list(set(atoms.select('all not protein and not ion').getResnames()))[0]
            ChainsHBs = [ ii for ii in HBS_calculations if ii[0][:3] == ligand_name or ii[3][:3] == ligand_name ]
        
        return ChainsHBs 
        

def calcSaltBridges(atoms, distA=4.5, **kwargs):
    """Finds salt bridges in protein structure.
    Histidine is not considered as a charge residue
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg distA: non-zero value, maximal distance between center of masses 
        of N and O atoms of negatively and positevely charged residues.
    :type distA: int, float, default is 4.5.

    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str
    Results can be displayed in VMD."""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    atoms_KRED = atoms.select('protein and resname ASP GLU LYS ARG and not backbone and not name OXT NE "C.*" and noh')
    charged_residues = list(set(zip(atoms_KRED.getResnums(), atoms_KRED.getChids())))
    
    LOGGER.info('Calculating salt bridges.')
    SaltBridges_list = []
    for i in charged_residues:
        sele1 = atoms_KRED.select('resid '+str(i[0])+' and chain '+i[1])
        try:
            sele1_center = calcCenter(sele1.getCoords())
            sele2 = atoms_KRED.select('same residue as exwithin '+str(distA)+' of center', center=sele1_center)
        except:
            sele1_center = sele1.getCoords()
            sele2 = atoms_KRED.select('same residue as exwithin '+str(distA)+' of center', center=sele1.getCoords())            
 
        if sele1 != None and sele2 != None:
            for ii in np.unique(sele2.getResnums()):                
                sele2_single = sele2.select('resid '+str(ii))
                try:
                    distance = calcDistance(sele1_center,calcCenter(sele2_single.getCoords()))
                except: 
                    distance = calcDistance(sele1_center,sele2_single.getCoords())
                
                if distance < distA and sele1.getNames()[0][0] != sele2_single.getNames()[0][0]:
                    SaltBridges_list.append([sele1.getResnames()[0]+str(sele1.getResnums()[0]), sele1.getNames()[0]+'_'+'_'.join(map(str,sele1.getIndices())), sele1.getChids()[0],
                                                  sele2_single.getResnames()[0]+str(sele2_single.getResnums()[0]), sele2_single.getNames()[0]+'_'+'_'.join(map(str,sele2_single.getIndices())), 
                                                  sele2_single.getChids()[0], round(distance,3)])
    
    SaltBridges_list = sorted(SaltBridges_list, key=lambda x : x[-1])
    [ SaltBridges_list.remove(j) for i in SaltBridges_list for j in SaltBridges_list if Counter(i) == Counter(j) ]
    SaltBridges_list_final = removeDuplicates(SaltBridges_list)
    SaltBridges_list_final2 = selectionByKwargs(SaltBridges_list_final, atoms, **kwargs)
    
    for kk in SaltBridges_list_final2:
        LOGGER.info("%10s%5s%16s  <---> %10s%5s%16s%8.1f" % (kk[0], kk[2], kk[1], kk[3], kk[5], kk[4], kk[6]))
        
    LOGGER.info("Number of detected salt bridges: {0}.".format(len(SaltBridges_list_final2)))        

    return SaltBridges_list_final2
    

def calcRepulsiveIonicBonding(atoms, distA=4.5, **kwargs):
    """Finds repulsive ionic bonding in protein structure
    i.e. between positive-positive or negative-negative residues.
    Histidine is not considered as a charged residue.
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg distA: non-zero value, maximal distance between center of masses 
            between N-N or O-O atoms of residues.
    :type distA: int, float, default is 4.5.

    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str
    Results can be displayed in VMD."""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    atoms_KRED = atoms.select('protein and resname ASP GLU LYS ARG and not backbone and not name OXT NE "C.*" and noh')
    charged_residues = list(set(zip(atoms_KRED.getResnums(), atoms_KRED.getChids())))
    
    LOGGER.info('Calculating repulsive ionic bonding.')
    RepulsiveIonicBonding_list = []
    for i in charged_residues:
        sele1 = atoms_KRED.select('resid '+str(i[0])+' and chain '+i[1])
        try:
            sele1_center = calcCenter(sele1.getCoords())
            sele2 = atoms_KRED.select('same residue as exwithin '+str(distA)+' of center', center=sele1_center)
        except:
            sele1_center = sele1.getCoords()
            sele2 = atoms_KRED.select('same residue as exwithin '+str(distA)+' of center', center=sele1.getCoords())            
 
        if sele1 != None and sele2 != None:
            for ii in np.unique(sele2.getResnums()):                
                sele2_single = sele2.select('resid '+str(ii))
                try:
                    distance = calcDistance(sele1_center,calcCenter(sele2_single.getCoords()))
                except: 
                    distance = calcDistance(sele1_center,sele2_single.getCoords())
                
                if distance < distA and sele1.getNames()[0][0] == sele2_single.getNames()[0][0] and sele1.getResnames()[0] != sele2_single.getResnames()[0]:
                    RepulsiveIonicBonding_list.append([sele1.getResnames()[0]+str(sele1.getResnums()[0]), sele1.getNames()[0]+'_'+'_'.join(map(str,sele1.getIndices())), sele1.getChids()[0],
                                                  sele2_single.getResnames()[0]+str(sele2_single.getResnums()[0]), sele2_single.getNames()[0]+'_'+'_'.join(map(str,sele2_single.getIndices())), 
                                                  sele2_single.getChids()[0], round(distance,3)])
    
    [ RepulsiveIonicBonding_list.remove(j) for i in RepulsiveIonicBonding_list for j in RepulsiveIonicBonding_list if Counter(i) == Counter(j) ]
    RepulsiveIonicBonding_list = sorted(RepulsiveIonicBonding_list, key=lambda x : x[-1])
    RepulsiveIonicBonding_list_final = removeDuplicates(RepulsiveIonicBonding_list)
    RepulsiveIonicBonding_list_final2 = selectionByKwargs(RepulsiveIonicBonding_list_final, atoms, **kwargs)
    
    for kk in RepulsiveIonicBonding_list_final2:
        LOGGER.info("%10s%5s%16s  <---> %10s%5s%16s%8.1f" % (kk[0], kk[2], kk[1], kk[3], kk[5], kk[4], kk[6]))
        
    LOGGER.info("Number of detected Repulsive Ionic Bonding interactions: {0}.".format(len(RepulsiveIonicBonding_list_final2)))
    
    return RepulsiveIonicBonding_list_final2


def calcPiStacking(atoms, distA=5.0, angle_min=0, angle_max=360, **kwargs):
    """Finds π–π stacking interactions (between aromatic rings).
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg distA: non-zero value, maximal distance between center of masses of residues aromatic rings.
    :type distA: int, float, default is 5.
    
    :arg angle_min: minimal angle between aromatic rings.
    :type angle_min: int, default is 0.

    :arg angle_max: maximal angle between rings.
    :type angle_max: int, default is 360.

    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str
    
    Results can be displayed in VMD.
    By default three residues are included TRP, PHE, TYR and HIS.
    Additional selection can be added: 
        >>> calcPiStacking(atoms, 'HSE'='noh and not backbone and not name CB')
        or
        >>> kwargs = {"HSE": "noh and not backbone and not name CB", "HSD": "noh and not backbone and not name CB"}
        >>> calcPiStacking(atoms,**kwargs)
    Predictions for proteins only. 
    To compute protein-ligand interactions use calcLigandInteractions() or define **kwargs"""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    aromatic_dic = {'TRP':'noh and not backbone and not name CB NE1 CD1 CG',
                'PHE':'noh and not backbone and not name CB',
                'TYR':'noh and not backbone and not name CB and not name OH',
                'HIS':'noh and not backbone and not name CB'}
    
    for key, value in kwargs.items():
        aromatic_dic[key] = value
    
    atoms_cylic = atoms.select('resname TRP PHE TYR HIS')
    aromatic_resids = list(set(zip(atoms_cylic.getResnums(), atoms_cylic.getChids())))

    LOGGER.info('Calculating Pi stacking interactions.')
    PiStack_calculations = []
    for i in aromatic_resids:
        for j in aromatic_resids:
            if i != j: 
                sele1_name = atoms.select('resid '+str(i[0])+' and chain '+i[1]+' and name CA').getResnames()
                sele1 = atoms.select('resid '+str(i[0])+' and chain '+i[1]+' and '+aromatic_dic[sele1_name[0]])
                
                sele2_name = atoms.select('resid '+str(j[0])+' and chain '+j[1]+' and name CA').getResnames()
                sele2 = atoms.select('resid '+str(j[0])+' and chain '+j[1]+' and '+aromatic_dic[sele2_name[0]])
                
                if sele1 != None and sele2 != None:
                    a1, b1, c1, a2, b2, c2 = calcPlane(sele1)[:3]+calcPlane(sele2)[:3]
                    RingRing_angle = calcAngleBetweenPlanes(a1, b1, c1, a2, b2, c2) # plane is computed based on 3 points of rings           
                    RingRing_distance = calcDistance(calcCenter(sele1.getCoords()),calcCenter(sele2.getCoords()))
                    if RingRing_distance < distA and angle_min < RingRing_angle < angle_max:
                        PiStack_calculations.append([str(sele1_name[0])+str(sele1.getResnums()[0]), '_'.join(map(str,sele1.getIndices())), str(sele1.getChids()[0]),
                                                     str(sele2_name[0])+str(sele2.getResnums()[0]), '_'.join(map(str,sele2.getIndices())), str(sele2.getChids()[0]),
                                                     round(RingRing_distance,3), round(RingRing_angle,3)])
    
    PiStack_calculations = sorted(PiStack_calculations, key=lambda x : x[-2])   
    PiStack_calculations_final = removeDuplicates(PiStack_calculations)
    PiStack_calculations_final2 = selectionByKwargs(PiStack_calculations_final, atoms, **kwargs)
    
    for kk in PiStack_calculations_final2:
        LOGGER.info("%10s%8s%32s  <---> %10s%8s%32s%8.1f%8.1f" % (kk[0], kk[2], kk[1], kk[3], kk[5], kk[4], kk[6], kk[7]))
        
    LOGGER.info("Number of detected Pi stacking interactions: {0}.".format(len(PiStack_calculations_final2)))
    
    return PiStack_calculations_final2


def calcPiCation(atoms, distA=5.0, extraSele=None, **kwargs):
    """Finds cation-Pi interaction i.e. between aromatic ring and positively charged residue (ARG and LYS)
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg distA: non-zero value, maximal distance between center of masses of aromatic ring and positively charge group.
    :type distA: int, float, default is 5.

    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str

    By default three residues are included TRP, PHE, TYR and HIS.
    Additional selection can be added in extraSele: 
        >>> calcPiCation(atoms, 'HSE'='noh and not backbone and not name CB')
        or
        >>> kwargs = {"HSE": "noh and not backbone and not name CB", "HSD": "noh and not backbone and not name CB"}
        >>> calcPiCation(atoms,**kwargs)
    Results can be displayed in VMD.
    Predictions for proteins only. To compute protein-ligand interactions use calcLigandInteractions() or define **kwargs"""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')
    
    aromatic_dic = {'TRP':'noh and not backbone and not name CB NE1 CD1 CG',
                'PHE':'noh and not backbone and not name CB',
                'TYR':'noh and not backbone and not name CB and not name OH',
                'HIS':'noh and not backbone and not name CB'}
        
    for key, value in kwargs.items():
        aromatic_dic[key] = value
        
    atoms_cylic = atoms.select('resname TRP PHE TYR HIS')
    aromatic_resids = list(set(zip(atoms_cylic.getResnums(), atoms_cylic.getChids())))

    PiCation_calculations = []
    LOGGER.info('Calculating cation-Pi interactions.')
    
    for i in aromatic_resids:
        sele1_name = atoms.select('resid '+str(i[0])+' and chain '+i[1]+' and name CA').getResnames()
        
        try:
            sele1 = atoms.select('resid '+str(i[0])+' and chain '+i[1]+' and '+aromatic_dic[sele1_name[0]])
            sele2 = atoms.select('(same residue as exwithin '+str(distA)+' of center) and resname ARG LYS and noh and not backbone and not name NE "C.*"', 
                               center=calcCenter(sele1.getCoords()))
        except:
            LOGGER.info("Missing atoms from the side chains of the structure. Use PDBFixer.")
        if sele1 != None and sele2 != None:
            for ii in np.unique(sele2.getResnums()):
                sele2_single = sele2.select('resid '+str(ii))
                try:
                    RingCation_distance = calcDistance(calcCenter(sele1.getCoords()),calcCenter(sele2_single.getCoords()))
                except: 
                    RingCation_distance = calcDistance(calcCenter(sele1.getCoords()),sele2_single.getCoords())
                
                if RingCation_distance < distA:
                    PiCation_calculations.append([str(sele1_name[0])+str(sele1.getResnums()[0]), '_'.join(map(str,sele1.getIndices())), str(sele1.getChids()[0]),
                                                  str(sele2_single.getResnames()[0])+str(sele2_single.getResnums()[0]), sele2_single.getNames()[0]+'_'+'_'.join(map(str,sele2_single.getIndices())), 
                                                  str(sele2_single.getChids()[0]), round(RingCation_distance,3)])
    
    PiCation_calculations = sorted(PiCation_calculations, key=lambda x : x[-1]) 
    PiCation_calculations_final = removeDuplicates(PiCation_calculations)
    PiCation_calculations_final2 = selectionByKwargs(PiCation_calculations_final, atoms, **kwargs)
    
    for kk in PiCation_calculations_final2:
        LOGGER.info("%10s%4s%32s  <---> %10s%4s%32s%8.1f" % (kk[0], kk[2], kk[1], kk[3], kk[5], kk[4], kk[6]))
        
    LOGGER.info("Number of detected cation-pi interactions: {0}.".format(len(PiCation_calculations_final2)))
    
    return PiCation_calculations_final2


def calcHydrophobic(atoms, distA=4.5, **kwargs): 
    """Prediction of hydrophobic interactions between hydrophobic residues (ALA, ILE, LEU, MET, PHE, TRP, VAL).
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg distA: non-zero value, maximal distance between atoms of hydrophobic residues.
    :type distA: int, float, default is 4.5.
    
    Additional selection can be added as shown below (with selection that includes only hydrophobic part): 
        >>> calcHydrophobic(atoms, 'XLE'='noh and not backbone')
    Predictions for proteins only. To compute protein-ligand interactions use calcLigandInteractions().
    Results can be displayed in VMD by using showVMDinteraction() 
    
    Note that interactions between aromatic residues are omitted becasue they are provided by calcPiStacking().    
    Results can be displayed in VMD."""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    Hydrophobic_list = []  
    atoms_hydrophobic = atoms.select('resname ALA VAL ILE MET LEU PHE TYR TRP')
    hydrophobic_resids = list(set(zip(atoms_hydrophobic.getResnums(), atoms_hydrophobic.getChids())))

    aromatic_nr = list(set(zip(atoms.aromatic.getResnums(),atoms.aromatic.getChids())))   
    aromatic = list(set(zip(atoms.aromatic.getResnames())))
    
    hydrophobic_dic = {'ALA': 'noh and not backbone', 'VAL': 'noh and not (backbone or name CB)',
    'ILE': 'noh and not (backbone or name CB)', 'LEU': 'noh and not (backbone or name CB)',
    'MET': 'noh and not (backbone or name CB)', 'PHE': 'noh and not (backbone or name CB)',
    'TYR': 'noh and not (backbone or name CB)', 'TRP': 'noh and not (backbone or name CB)'}

    #for key, value in kwargs.items():
    #    hydrophobic_dic[key] = value
    
    LOGGER.info('Calculating hydrophobic interactions.')
    Hydrophobic_calculations = []
    for i in hydrophobic_resids:
        try:
            sele1_name = atoms.select('resid '+str(i[0])+' and chain '+i[1]+' and name CA').getResnames()
            sele1 = atoms.select('resid '+str(i[0])+' and '+' chain '+i[1]+' and '+hydrophobic_dic[sele1_name[0]]) 
            sele1_nr = sele1.getResnums()[0]  
            sele2 = atoms.select('(same residue as exwithin '+str(distA)+' of (resid '+str(sele1_nr)+' and chain '+i[1]+' and resname '+sele1_name[0]+
                               ')) and ('+' or '.join([ '(resname '+item[0]+' and '+item[1]+')' for item in hydrophobic_dic.items() ])+')')

        except:
            LOGGER.info("Missing atoms from the side chains of the structure. Use PDBFixer.")
            sele1 = None
            sele2 = None
        
        if sele2 != None:
            sele2_nr = list(set(zip(sele2.getResnums(), sele2.getChids())))

            if sele1_name[0] in aromatic:
                sele2_filter = sele2.select('all and not (resname TYR PHE TRP or resid '+str(i)+')')
                if sele2_filter != None:
                    listOfAtomToCompare = cleanNumbers(findNeighbors(sele1, distA, sele2_filter))
                
            elif sele1_name[0] not in aromatic and i in sele2_nr:
                sele2_filter = sele2.select(sele2.select('all and not (resid '+str(i[0])+' and chain '+i[1]+')'))
                if sele2_filter != None:
                    listOfAtomToCompare = cleanNumbers(findNeighbors(sele1, distA, sele2_filter))
            else:
                listOfAtomToCompare = cleanNumbers(findNeighbors(sele1, distA, sele2))
                                                           
            if listOfAtomToCompare != []:
                listOfAtomToCompare = sorted(listOfAtomToCompare, key=lambda x : x[-1])
                minDistancePair = listOfAtomToCompare[0]
                if minDistancePair[-1] < distA:
                    sele1_new = atoms.select('index '+str(minDistancePair[0])+' and name '+str(minDistancePair[2]))
                    sele2_new = atoms.select('index '+str(minDistancePair[1])+' and name '+str(minDistancePair[3]))
                    Hydrophobic_calculations.append([sele1_new.getResnames()[0]+str(sele1_new.getResnums()[0]), 
                                                             minDistancePair[2]+'_'+str(minDistancePair[0]), sele1_new.getChids()[0],
                                                             sele2_new.getResnames()[0]+str(sele2_new.getResnums()[0]), 
                                                             minDistancePair[3]+'_'+str(minDistancePair[1]), sele2_new.getChids()[0],
                                                             round(minDistancePair[-1],3)]) 
                    
    Hydrophobic_calculations = sorted(Hydrophobic_calculations, key=lambda x : x[-1])
    Hydrophobic_calculations_final = removeDuplicates(Hydrophobic_calculations)
    Hydrophobic_calculations_final2 = selectionByKwargs(Hydrophobic_calculations_final, atoms, **kwargs)
    
    for kk in Hydrophobic_calculations_final2:
        LOGGER.info("%10s%5s%14s  <---> %10s%5s%14s%8.1f" % (kk[0], kk[2], kk[1], kk[3], kk[5], kk[4], kk[6]))
        
    LOGGER.info("Number of detected hydrophobic interactions: {0}.".format(len(Hydrophobic_calculations_final2)))
    
    return Hydrophobic_calculations_final2


def calcDisulfideBonds(atoms, distA=2.5):
    """Prediction of disulfide bonds.
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg distA: non-zero value, maximal distance between atoms of hydrophobic residues.
    :type distA: int, float, default is 2.5."""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    try:
        atoms_SG = atoms.select('protein and resname CYS')
    except AttributeError:
        try:
            checkCoords(atoms_SG)
        except TypeError:
            raise TypeError('Lack of cysteines in the structure.')
    
    atoms_SG = atoms.select('protein and resname CYS and name SG')
    atoms_SG_res = list(set(zip(atoms_SG.getResnums(), atoms_SG.getChids())))
    
    LOGGER.info('Calculating disulfide bonds.')
    DisulfideBonds_list = []
    for i in atoms_SG_res:
        CYS_pairs = atoms.select('(same residue as protein within '+str(distA)+' of ('+'resid '+str(i[0])+' and chain '+i[1]+' and name SG)) and (resname CYS and name SG)')
        CYSresnames = [j+str(i) for i, j in zip(CYS_pairs.getResnums(), CYS_pairs.getResnames())]
        if len(CYSresnames) != 1 and len(CYSresnames) != 0:
            DisulfideBonds_list.append(list(zip(CYSresnames, CYS_pairs.getChids())))

    DisulfideBonds_list2 = list({tuple(sorted(i)) for i in DisulfideBonds_list})
    
    if len(DisulfideBonds_list2) != 0:
        return DisulfideBonds_list2
    else:
        LOGGER.info('Lack of disulfide bonds in the structure.')
    

def calcMetalInteractions(atoms, distA=3.0, extraIons=['FE'], excluded_ions=['SOD', 'CLA']):
    """Interactions with metal ions (includes water, ligands and other ions).
        
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg distA: non-zero value, maximal distance between ion and residue.
    :type distA: int, float, default is 3.0.
    
    :arg extraIons: ions to be included in the analysis.
    :type extraIons: list
    
    :arg excluded_ions: ions which should be excluded from the analysis.
    :type excluded_ions: list """
    
    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')
    
    try:
        atoms_ions = atoms.select('ion and not name '+' '.join(excluded_ions)+' or (name '+' '.join(map(str,extraIons))+')')
        MetalResList = []
        MetalRes_calculations = cleanNumbers(findNeighbors(atoms_ions, distA, atoms.select('all and noh')))
        for i in MetalRes_calculations:
            if i[-1] != 0:
                MetalResList.append([atoms.getResnames()[i[0]]+str(atoms.getResnums()[i[0]]), i[2], 
                                 atoms.getResnames()[i[1]]+str(atoms.getResnums()[i[1]]), i[3], i[-1]])

        return MetalResList
        
    except TypeError:
        raise TypeError('An object should contain ions')


def calcProteinInteractions(atoms, **kwargs):
    """Compute all protein interactions (shown below) using default parameters.
        (1) Hydrogen bonds
        (2) Salt Bridges
        (3) RepulsiveIonicBonding 
        (4) Pi stacking interactions
        (5) Pi-cation interactions
        (6) Hydrophobic interactions
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str """

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    LOGGER.info('Calculating all interations.') 
    HBs_calculations = calcHydrogenBonds(atoms.protein, **kwargs)               #1 in scoring
    SBs_calculations = calcSaltBridges(atoms.protein, **kwargs)                 #2
    SameChargeResidues = calcRepulsiveIonicBonding(atoms.protein, **kwargs)     #3
    Pi_stacking = calcPiStacking(atoms.protein, **kwargs)                       #4
    Pi_cation = calcPiCation(atoms.protein, **kwargs)                           #5
    Hydroph_calculations = calcHydrophobic(atoms.protein, **kwargs)             #6
    AllInteractions = [HBs_calculations, SBs_calculations, SameChargeResidues, Pi_stacking, Pi_cation, Hydroph_calculations]   
    
    return AllInteractions


def calcHydrogenBondsDCD(atoms, trajectory, distA=3.0, angle=40, cutoff_dist=20, **kwargs):   
    """Compute hydrogen bonds for DCD trajectory using default parameters.
        
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
        
    :arg trajectory: trajectory file
    :type trajectory: class:`.Trajectory`

    :arg distA: non-zero value, maximal distance between donor and acceptor.
    :type distA: int, float, default is 3.0
    
    :arg angle: non-zero value, maximal (180 - D-H-A angle) (donor, hydrogen, acceptor).
    :type angle: int, float, default is 40.
    
    :arg cutoff_dist: non-zero value, interactions will be found between atoms with index differences
        that are higher than cutoff_dist.
        default is 20 atoms.
    :type cutoff_dist: int
    
    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str"""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')
        
    if isinstance(trajectory, Atomic):
        trajectory = Ensemble(trajectory)
                        
    HBs_all = []
    trajectory.reset()
        
    for j0, frame0 in enumerate(trajectory):  
        LOGGER.info('Frame: {0}'.format(j0))
        protein = atoms.select('protein')
        hydrogen_bonds = calcHydrogenBonds(protein, distA, angle, cutoff_dist, **kwargs)
        HBs_all.append(hydrogen_bonds)
        
    return HBs_all


def calcSaltBridgesDCD(atoms, trajectory, distA=4.5, **kwargs):
    """Compute salt bridges for DCD trajectory using default parameters.
        
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`

    :arg trajectory: trajectory file
    :type trajectory: class:`.Trajectory`
    
    :arg distA: non-zero value, maximal distance between center of masses 
        of N and O atoms of negatively and positevely charged residues.
    :type distA: int, float, default is 4.5.
    
    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str"""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    if isinstance(trajectory, Atomic):
        trajectory = Ensemble(trajectory)        
                        
    SBs_all = []
    trajectory.reset()
        
    for j0, frame0 in enumerate(trajectory):  
        LOGGER.info('Frame: {0}'.format(j0))
        protein = atoms.select('protein')
        salt_bridges = calcSaltBridges(protein, distA, **kwargs)
        SBs_all.append(salt_bridges)
        
    return SBs_all
    

def calcRepulsiveIonicBondingDCD(atoms, trajectory, distA=4.5, **kwargs):  
    """Compute repulsive ionic bonding for DCD trajectory using default parameters.
        
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`

    :arg trajectory: trajectory file
    :type trajectory: class:`.Trajectory`
    
    :arg distA: non-zero value, maximal distance between center of masses 
            between N-N or O-O atoms of residues.
    :type distA: int, float, default is 4.5.

    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str"""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    if isinstance(trajectory, Atomic):
        trajectory = Ensemble(trajectory)        
                        
    RIB_all = []
    trajectory.reset()
        
    for j0, frame0 in enumerate(trajectory):  
        LOGGER.info('Frame: {0}'.format(j0))
        protein = atoms.select('protein')
        rib = calcRepulsiveIonicBonding(protein, distA, **kwargs)
        RIB_all.append(rib)
        
    return RIB_all


def calcPiStackingDCD(atoms, trajectory, distA=5.0, angle_min=0, angle_max=360, **kwargs):   
    """Compute Pi-stacking interactions for DCD trajectory using default parameters.
        
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
      
    :arg trajectory: trajectory file
    :type trajectory: class:`.Trajectory`
    
    :arg distA: non-zero value, maximal distance between center of masses of residues aromatic rings.
    :type distA: int, float, default is 5.
    
    :arg angle_min: minimal angle between aromatic rings.
    :type angle_min: int, default is 0.

    :arg angle_max: maximal angle between rings.
    :type angle_max: int, default is 360.
    
    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str"""            

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')
    if isinstance(trajectory, Atomic):
        trajectory = Ensemble(trajectory)        
                        
    pi_stack_all = []
    trajectory.reset()
        
    for j0, frame0 in enumerate(trajectory):  
        LOGGER.info('Frame: {0}'.format(j0))
        protein = atoms.select('protein')
        pi_stack = calcPiStacking(protein, distA, angle_min, angle_max, **kwargs)
        pi_stack_all.append(pi_stack)
        
    return pi_stack_all


def calcPiCationDCD(atoms, trajectory, distA=5.0, extraSele=None, **kwargs):  
    """Compute Pi-cation interactions for DCD trajectory using default parameters.
        
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
        
    :arg trajectory: trajectory file
    :type trajectory: class:`.Trajectory`
    
    :arg distA: non-zero value, maximal distance between center of masses of aromatic ring and positively charge group.
    :type distA: int, float, default is 5.
    
    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str"""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    if isinstance(trajectory, Atomic):
        trajectory = Ensemble(trajectory)        
                        
    pi_cat_all = []
    trajectory.reset()
        
    for j0, frame0 in enumerate(trajectory):  
        LOGGER.info('Frame: {0}'.format(j0))
        protein = atoms.select('protein')
        pi_cat = calcPiCation(protein, distA, extraSele, **kwargs)
        pi_cat_all.append(pi_cat)
        
    return pi_cat_all


def calcHydrophobicDCD(atoms, trajectory, distA=4.5, **kwargs):  
    """Compute hydrophobic interactions for DCD trajectory using default parameters.
        
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
        
    :arg trajectory: trajectory file
    :type trajectory: class:`.Trajectory`
    
    :arg distA: non-zero value, maximal distance between atoms of hydrophobic residues.
    :type distA: int, float, default is 4.5.

    :arg selection: selection string
    :type selection: str
    
    :arg selection2: selection string
    :type selection2: str"""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    if isinstance(trajectory, Atomic):
        trajectory = Ensemble(trajectory)        
                        
    HPh_all = []
    trajectory.reset()
        
    for j0, frame0 in enumerate(trajectory):  
        LOGGER.info('Frame: {0}'.format(j0))
        protein = atoms.select('protein')
        HPh = calcHydrophobic(protein, distA, **kwargs)
        HPh_all.append(HPh)
        
    return HPh_all


def calcDisulfideBondsDCD(atoms, trajectory, distA=2.5):
    """Compute disulfide bonds for DCD trajectory using default parameters.
        
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
        
    :arg trajectory: trajectory file
    :type trajectory: class:`.Trajectory`
    
    :arg distA: non-zero value, maximal distance between atoms of hydrophobic residues.
    :type distA: int, float, default is 2.5."""

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    if isinstance(trajectory, Atomic):
        trajectory = Ensemble(trajectory)        
                        
    DiBs_all = []
    trajectory.reset()
        
    for j0, frame0 in enumerate(trajectory):  
        LOGGER.info('Frame: {0}'.format(j0))
        protein = atoms.select('protein')
        disulfide_bonds = calcDisulfideBonds(protein, distA)
        DiBs_all.append(disulfide_bonds)
        
    return DiBs_all


def compareInteractions(data1, data2, **kwargs):
    """Comparison of two outputs from interactions. 
    It will provide information about the disappearance and appearance of some interactions
    as well as the similarities in the interactions
    for the same system. Two conformations can be compared.
    
    :arg data1: list with interactions from calcHydrogenBonds() or other types
    :type data1: list
 
    :arg data2: list with interactions from calcHydrogenBonds() or other types
    :type data2: list
    
    :arg filename: name of text file in which the comparison between two sets of interactions 
                will be saved 
    type filename: str 
    
    Example of usage: 
    >>> atoms1 = parsePDB('PDBfile1.pdb').select('protein')
    >>> atoms2 = parsePDB('PDBfile2.pdb').select('protein')
    >>> compareInteractions(calcHydrogenBonds(atoms1), calcHydrogenBonds(atoms2))
    """
    
    if not isinstance(data1, list):
        raise TypeError('data1 must be a list of interactions.')

    if not isinstance(data2, list):
        raise TypeError('data2 must be a list of interactions.')        

    data1_tuple = [ tuple([i[0]+i[2], i[3]+i[5]]) for i in data1 ]
    data2_tuple = [ tuple([i[0]+i[2], i[3]+i[5]]) for i in data2 ]
    diff_21 = set(data2_tuple) - set(data1_tuple)
    diff_12 = set(data1_tuple) - set(data2_tuple)
    similar_12 = set(data1_tuple) & set(data2_tuple)
    
    LOGGER.info("Which interactions disappeared: {0}".format(len(diff_21)))
    for j in diff_21:
        LOGGER.info('{0} <---> {1}'.format(j[0],j[1]))
        
    LOGGER.info("\nWhich interactions appeared: {0}".format(len(diff_12)))  
    for j in diff_12:  
        LOGGER.info('{0} <---> {1}'.format(j[0],j[1]))
    
    LOGGER.info("Which interactions are the same: {0}".format(len(similar_12)))
    for j in similar_12:
        if len(similar_12) != 0:
            LOGGER.info('{0} <---> {1}'.format(j[0],j[1]))
        else: LOGGER.info("None")
    
    try:
        if 'filename' in kwargs:
            with open(kwargs['filename'], 'w') as f:  # what disapperaed from initial
                f.write("Which interactions disappeared:\n")
                for i in diff_21:
                    f.write(i[0]+'-'+i[1]+'\n')
                f.write("\nWhich interactions appeared:\n")
                for i in diff_12:
                    f.write(i[0]+'-'+i[1]+'\n')
                f.write("\nWhich interactions are the same:\n")
                for i in similar_12:
                    f.write(i[0]+'-'+i[1]+'\n')
            f.close()
    except: pass
    
    return diff_21, diff_12, similar_12
    
    
def calcStatisticsInteractions(data):
    """Return the statistics of interactions from DCD trajectory including
    the number of counts for each residue pair, 
    average distance of interactions for each pair [in Ang] and standard deviation.
        
    :arg data: list with interactions from calcHydrogenBondsDCD() or other types
    :type data: list
    
    Example of usage: 
    >>> atoms = parsePDB('PDBfile.pdb')
    >>> dcd = Trajectory('DCDfile.dcd')
    >>> dcd.link(atoms)
    >>> dcd.setCoords(atoms)
    
    >>> data = calcPiCationDCD(atoms, dcd, distA=5)
    or
    >>> interactionsDCD = InteractionsDCD()
    >>> data = interactionsDCD.getPiCation()
    """
    
    interactions_list = [ (jj[0]+jj[2]+'-'+jj[3]+jj[5], jj[6]) for ii in data for jj in ii]
    import numpy as np
    elements = [t[0] for t in interactions_list]
    stats = {}

    for element in elements:
        if element not in stats:
            values = [t[1] for t in interactions_list if t[0] == element]
            stats[element] = {
                "stddev": np.round(np.std(values),2),
                "mean": np.round(np.mean(values),2),
                "count": len(values)
            }

    statistic = []
    for key, value in stats.items():
        LOGGER.info("Statistics for {0}:".format(key))
        LOGGER.info("  Average [Ang.]: {}".format(value['mean']))
        LOGGER.info("  Standard deviation [Ang.]: {0}".format(value['stddev']))
        LOGGER.info("  Count: {0}".format(value['count']))
        statistic.append([key, value['count'], value['mean'], value['stddev']])
    
    statistic.sort(key=lambda x: x[1], reverse=True)
    return statistic
    

def calcLigandInteractions(atoms, **kwargs):
    """Provide ligand interactions with other elements of the system including protein, water and ions.
    Results are computed by PLIP [SS15]_ which should be installed.
    Note that PLIP will not recognize ligand unless it will be HETATM in the PDB file.
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg select: a selection string for residues of interest
            default is 'all not (water or protein or ion)'
    :type select: str
    
    :arg ignore_ligs: List of ligands which will be excluded from the analysis.
    :type ignore_ligs: list
    
    To display results as a list of interactions use listLigandInteractions()
    and for visualization in VMD please use showLigandInteraction_VMD() 
    
    Requirements of usage:
    ## Instalation of Openbabel:
    >>> conda install -c conda-forge openbabel    
    ## https://anaconda.org/conda-forge/openbabel
    
    ## Instalation of PLIP
    >>> conda install -c conda-forge plip
    ## https://anaconda.org/conda-forge/plip
    # https://github.com/pharmai/plip/blob/master/DOCUMENTATION.md

    .. [SS15] Salentin S., Schreiber S., Haupt V. J., Adasme M. F., Schroeder M.  
    PLIP: fully automated protein–ligand interaction profiler 
    *Nucl. Acids Res.* **2015** 43:W443-W447.  """
    
    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')
    try:
        from plip.structure.preparation import PDBComplex   
        
        pdb_name = atoms.getTitle()+'_sele.pdb'
        LOGGER.info("Writing PDB file with selection in the local directory.")
        writePDB(pdb_name, atoms)

        try:
            if atoms.hydrogen == None or atoms.hydrogen.numAtoms() < 30: # if there is no hydrogens in PDB structure
                addHydrogens(pdb_name)
                pdb_name = pdb_name[:-4]+'_addH.pdb'
                atoms = parsePDB(pdb_name)
                LOGGER.info("Lack of hydrogens in the structure. Hydrogens have been added.")
        except: 
            LOGGER.info("Install Openbabel to add missing hydrogens or provide structure with hydrogens")
    
        Ligands = [] # Ligands can be more than one
        my_mol = PDBComplex()
        my_mol.load_pdb(pdb_name) # Load the PDB file into PLIP class
        
        if 'select' in kwargs:
            select = kwargs['select']
            LOGGER.info('Selection will be replaced.')
        else:
            select='all not (water or protein or ion)'
            LOGGER.info('Default selection will be used.')

        if 'ignore_ligs' in kwargs:
            ignore_ligs = kwargs['ignore_ligs']
            LOGGER.info('Ignoring list of ligands is uploaded.')
        else:
            ignore_ligs=['NAG','BMA','MAN']
            LOGGER.info('Three molecules will be ignored from analysis: NAG, BMA and MAN.')
        
        select = select+' and not (resname '+' '.join(ignore_ligs)+')'
        ligand_select = atoms.select(select)
        analyzedLigand = []
        LOGGER.info("Detected ligands: ")
        for i in range(len(ligand_select.getResnums())): # It has to be done by each atom
            try:
                ResID = ligand_select.getResnames()[i]
                ChainID = ligand_select.getChids()[i]
                ResNames = ligand_select.getResnums()[i]
                my_bsid = str(ResID)+':'+str(ChainID)+':'+str(ResNames)
                if my_bsid not in analyzedLigand: 
                    LOGGER.info(my_bsid)
                    analyzedLigand.append(my_bsid)
                    my_mol.analyze()
                    my_interactions = my_mol.interaction_sets[my_bsid] # Contains all interaction data      
                    Ligands.append(my_interactions)
            except: 
                LOGGER.info(my_bsid+" not analyzed")

        return Ligands, analyzedLigand

    except:
        LOGGER.info("Install Openbabel and PLIP.")


def listLigandInteractions(PLIP_output):
    """Create a list of interactions from PLIP output created using calcLigandInteractions().
    Results can be displayed in VMD. 
    
    :arg PLIP_output: Results from PLIP for protein-ligand interactions.
    :type PLIP_output: PLIP object obtained from calcLigandInteractions() 
    
    Note that five types of interactions are considered: hydrogen bonds, salt bridges, pi-stacking,
    cation-pi, hydrophobic and water bridges."""
    
    Inter_list_all = []
    for i in PLIP_output.all_itypes:
        param_inter = [method for method in dir(i) if method.startswith('_') is False]
        
        #LOGGER.info(str(type(i)).split('.')[-1].strip("'>"))
        
        if str(type(i)).split('.')[-1].strip("'>") == 'hbond':
            Inter_list = ['hbond',i.restype+str(i.resnr), i[0].type+'_'+str(i.d_orig_idx), i.reschain,
                          i.restype+str(i.resnr_l), i[2].type+'_'+str(i.a_orig_idx), i.reschain_l, 
                          i.distance_ad, i.angle, i[0].coords, i[2].coords]
     
        if str(type(i)).split('.')[-1].strip("'>") == 'saltbridge':
            Inter_list = ['saltbridge',i.restype+str(i.resnr), '_'.join(map(str,i.negative.atoms_orig_idx)), i.reschain,
                          i.restype+str(i.resnr_l), '_'.join(map(str,i.positive.atoms_orig_idx)), i.reschain_l, 
                          i.distance, None, i.negative.center, i.positive.center]
                 
        if str(type(i)).split('.')[-1].strip("'>") == 'pistack':
             Inter_list = ['pistack',i.restype+str(i.resnr), '_'.join(map(str,i[0].atoms_orig_idx)), i.reschain,
                          i.restype+str(i.resnr_l), '_'.join(map(str,i[1].atoms_orig_idx)), i.reschain_l, 
                          i.distance, i.angle, i[0].center, i[1].center]           
        
        if str(type(i)).split('.')[-1].strip("'>") == 'pication':
             Inter_list = ['pication',i.restype+str(i.resnr), '_'.join(map(str,i[0].atoms_orig_idx)), i.reschain,
                          i.restype+str(i.resnr_l), '_'.join(map(str,i[1].atoms_orig_idx)), i.reschain_l, 
                          i.distance, None, i[0].center, i[1].center]                       
        
        if str(type(i)).split('.')[-1].strip("'>") == 'hydroph_interaction':
            Inter_list = ['hydroph_interaction',i.restype+str(i.resnr), i[0].type+'_'+str(i[0].idx), i.reschain,
                          i.restype+str(i.resnr_l), i[2].type+'_'+str(i[2].idx), i.reschain_l, 
                          i.distance, None, i[0].coords, i[2].coords]           
             
        if str(type(i)).split('.')[-1].strip("'>") == 'waterbridge':
            water = i.water
            Inter_list = ['waterbridge',i.restype+str(i.resnr), i[0].type+'_'+str(i[0].idx), i.reschain,
                          i.restype+str(i.resnr_l), i[3].type+'_'+str(i[3].idx), i.reschain_l, 
                          [i.distance_aw, i.distance_dw], [i.d_angle, i.w_angle], i[0].coords, i[3].coords, 
                          i.water.coords, i[7].residue.name+'_'+str(i[7].residue.idx)]    
        else: pass
                      
        Inter_list_all.append(Inter_list)               
    
    for nr_k,k in enumerate(Inter_list_all):
        LOGGER.info("%3i%22s%10s%26s%4s  <---> %8s%12s%4s%6.1f" % (nr_k,k[0],k[1],k[2],k[3],k[4],k[5],k[6],k[7]))
    
    return Inter_list_all


def showProteinInteractions_VMD(atoms, interactions, color='red',**kwargs):
    """Save information about protein interactions to a TCL file (filename)
    which can be further use in VMD to display all intercations in a graphical interface
    (in TKConsole: play script_name.tcl).
    Different types of interactions can be saved separately (color can be selected) 
    or all at once for all types of interactions (hydrogen bonds - blue, salt bridges - yellow,
    pi stacking - green, cation-pi - orange and hydrophobic - silver).
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg interactions: List of interactions for protein interactions.
    :type interactions: List of lists
    
    :arg color: color to draw interactions in VMD,
                not used only for single interaction type.
    :type color: str or **None**, by default `red`.
    
    :arg filename: name of TCL file where interactions will be saved.
    :type filename: str
        
    Example (hydrogen bonds for protein only): 
    >>> interactions = calcHydrogenBonds(atoms.protein, distA=3.2, angle=30)
    or all interactions at once:
    >>> interactions = calcProteinInteractions(atoms.protein) """

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    if not isinstance(interactions, list):
        raise TypeError('interactions must be a list of interactions.')
    
    try:
        filename = kwargs['filename']
    except:
        filename = atoms.getTitle()+'_interaction.tcl'
    
    tcl_file = open(filename, 'w') 
    
    
    def TCLforSingleInteraction(interaction, color='blue', tcl_file=tcl_file):
        """Creates TCL file for the VMD program based on the interactions
        computed by 
        
        :arg interactions: List of interactions for protein interactions.
        :type interactions: List of lists
        
        :arg color: Name of the color which will be used for the visualization of 
                    interactions in VMD
        :type color: str
        
        :arg tcl_file: name of the TCL file which will be saved for visualization                
        :type tcl_file: str """
        
        tcl_file.write('draw color '+color+'\n')
        for nr_i,i in enumerate(interaction):
            try:
                at1 = atoms.select('index '+' '.join([k for k in i[1].split('_') if k.isdigit() ] ))
                at1_atoms = ' '.join(map(str,list(calcCenter(at1.getCoords()))))
                at2 = atoms.select('index '+' '.join([kk for kk in i[4].split('_') if kk.isdigit() ] ))
                at2_atoms = ' '.join(map(str,list(calcCenter(at2.getCoords()))))
                            
                tcl_file.write('draw line {'+at1_atoms+'} {'+at2_atoms+'} style dashed width 4\n')
                
                tcl_file.write('mol color Name\n')
                tcl_file.write('mol representation Licorice 0.100000 12.000000 12.000000\n')
                tcl_file.write('mol selection (resname '+at1.getResnames()[0]+' and resid '+str(at1.getResnums()[0])
                               +' and chain '+at1.getChids()[0]+' and noh) or (resname '+at2.getResnames()[0]+' and resid '
                               +str(at2.getResnums()[0])+' and chain '+at2.getChids()[0]+' and noh)\n')
                tcl_file.write('mol material Opaque\n')
                tcl_file.write('mol addrep 0 \n')
            except: LOGGER.info("There was a problem.")
     
    if len(interactions) == 6:   
        # For all six types of interactions at once
        # HBs_calculations, SBs_calculations, SameChargeResidues, Pi_stacking, Pi_cation, Hydroph_calculations
        colors = ['blue', 'yellow', 'red', 'green', 'orange', 'silver']
        
        for nr_inter,inter in enumerate(interactions):
            TCLforSingleInteraction(inter, color=colors[nr_inter], tcl_file=tcl_file)

    elif len(interactions[0]) == 0 or interactions == []:
        LOGGER.info("Lack of results")
        
    else:
        TCLforSingleInteraction(interactions,color)

    tcl_file.write('draw materials off')
    tcl_file.close()   
    LOGGER.info("TCL file saved")


def showLigandInteraction_VMD(atoms, interactions, **kwargs):
    """Save information from PLIP for ligand-protein interactions in a TCL file
    which can be further used in VMD to display all intercations in a graphical 
    interface (hydrogen bonds - `blue`, salt bridges - `yellow`,
    pi stacking - `green`, cation-pi - `orange`, hydrophobic - `silver` and water bridges - `cyan`).
    
    :arg atoms: an Atomic object from which residues are selected
    :type atoms: :class:`.Atomic`
    
    :arg interactions: List of interactions for protein-ligand interactions.
    :type interactions: List of lists
    
    :arg filename: name of TCL file where interactions will be saved.
    :type filename: str

    To obtain protein-ligand interactions:
    >>> calculations = calcLigandInteractions(atoms)
    >>> interactions = listLigandInteractions(calculations) """

    try:
        coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                    atoms.getCoords())
    except AttributeError:
        try:
            checkCoords(coords)
        except TypeError:
            raise TypeError('coords must be an object '
                            'with `getCoords` method')

    if not isinstance(interactions, list):
        raise TypeError('interactions must be a list of interactions.')
    
    try:
        filename = kwargs['filename']
    except:
        filename = atoms.getTitle()+'_interaction.tcl'
    
    tcl_file = open(filename, 'w') 
    
    if len(interactions[0]) >= 10: 
        dic_color = {'hbond':'blue','pistack':'green','saltbridge':'yellow','pication':'orange',
                     'hydroph_interaction':'silver','waterbridge':'cyan'}
        
        for i in interactions:
            tcl_file.write('draw color '+dic_color[i[0]]+'\n')
            
            if i[0] == 'waterbridge':
                hoh_id = atoms.select('x `'+str(i[11][0])+'` and y `'+str(i[11][1])+'` and z `'+str(i[11][2])+'`').getResnums()[0]
                tcl_file.write('draw line {'+str(' '.join(map(str,i[9])))+'} {'+str(' '.join(map(str,i[11])))+'} style dashed width 4\n')
                tcl_file.write('draw line {'+str(' '.join(map(str,i[10])))+'} {'+str(' '.join(map(str,i[11])))+'} style dashed width 4\n')
                tcl_file.write('mol color Name\n')
                tcl_file.write('mol representation Licorice 0.100000 12.000000 12.000000\n')
                tcl_file.write('mol selection (resname '+i[1][:3]+' and resid '+str(i[1][3:])
                               +' and chain '+i[3]+' and noh) or (resname '+i[4][:3]+' and resid '
                               +str(i[4][3:])+' and chain '+i[6]+' and noh) or (water and resid '+str(hoh_id)+')\n')
                
            else:
                tcl_file.write('draw line {'+str(' '.join(map(str,i[9])))+'} {'+str(' '.join(map(str,i[10])))+'} style dashed width 4\n')
                tcl_file.write('mol color Name\n')
                tcl_file.write('mol representation Licorice 0.100000 12.000000 12.000000\n')
                tcl_file.write('mol selection (resname '+i[1][:3]+' and resid '+str(i[1][3:])
                               +' and chain '+i[3]+' and noh) or (resname '+i[4][:3]+' and resid '
                               +str(i[4][3:])+' and chain '+i[6]+' and noh)\n')
            tcl_file.write('mol material Opaque\n')
            tcl_file.write('mol addrep 0 \n')            


    tcl_file.write('draw materials off')
    tcl_file.close()   
    LOGGER.info("TCL file saved")


class Interactions(object):

    """Class for Interaction analysis of proteins."""

    def __init__(self, title='Unknown'):
        self._title = str(title).strip()
        self._atoms = None
        self._interactions = None
        self._interactions_matrix = None
        self._hbs = None
        self._sbs = None
        self._rib = None
        self._piStack = None
        self._piCat = None
        self._hps = None
        #super(Interactions, self).__init__(name)


    def setTitle(self, title):
        """Set title of the model."""

        self._title = str(title)
        
           
    def calcProteinInteractions(self, atoms, **kwargs):
        """Compute all protein interactions (shown below) using default parameters.
            (1) Hydrogen bonds
            (2) Salt Bridges
            (3) RepulsiveIonicBonding 
            (4) Pi stacking interactions
            (5) Pi-cation interactions
            (6) Hydrophobic interactions
        
        :arg atoms: an Atomic object from which residues are selected
        :type atoms: :class:`.Atomic`"""

        try:
            coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                        atoms.getCoords())
        except AttributeError:
            try:
                checkCoords(coords)
            except TypeError:
                raise TypeError('coords must be an object '
                                'with `getCoords` method')

        LOGGER.info('Calculating all interations.') 
        HBs_calculations = calcHydrogenBonds(atoms.protein, **kwargs)               #1 in scoring
        SBs_calculations = calcSaltBridges(atoms.protein, **kwargs)                 #2
        SameChargeResidues = calcRepulsiveIonicBonding(atoms.protein, **kwargs)     #3
        Pi_stacking = calcPiStacking(atoms.protein, **kwargs)                       #4
        Pi_cation = calcPiCation(atoms.protein, **kwargs)                           #5
        Hydroph_calculations = calcHydrophobic(atoms.protein, **kwargs)             #6
        AllInteractions = [HBs_calculations, SBs_calculations, SameChargeResidues, Pi_stacking, Pi_cation, Hydroph_calculations]   
        
        self._atoms = atoms
        self._interactions = AllInteractions
        
        self._hbs = HBs_calculations
        self._sbs = SBs_calculations
        self._rib = SameChargeResidues
        self._piStack = Pi_stacking
        self._piCat = Pi_cation
        self._hps = Hydroph_calculations
        
        return self._interactions

    
    def getAtoms(self):
        """Returns associated atoms"""

        return self._atoms

    def getInteractions(self):
        """Returns the list of all interactions"""
        
        return self._interactions
    
    def getHydrogenBonds(self):
        """Returns the list of hydrogen bonds"""
        
        return self._hbs
        
    def getSaltBridges(self):
        """Returns the list of salt bridges"""
        
        return self._sbs

    def getRepulsiveIonicBonding(self):
        """Returns the list of repulsive ionic bonding"""
        
        return self._rib
        
    def getPiStacking(self):
        """Returns the list of Pi-stacking interactions"""
        
        return self._piStack

    def getPiCation(self):
        """Returns the list of Pi-cation interactions"""
        
        return self._piCat
        
    def getHydrophobic(self):
        """Returns the list of hydrophobic interactions"""
        
        return self._hps

    def setNewHydrogenBonds(self, interaction):
        """Replace default calculation of hydrogen bonds by the one provided by user"""

        self._interactions[0] = interaction
        self._hbs = self._interactions[0]    
        LOGGER.info('Hydrogen Bonds are replaced')

    def setNewSaltBridges(self, interaction):
        """Replace default calculation of salt bridges by the one provided by user"""

        self._interactions[1] = interaction
        self._sbs = self._interactions[1]  
        LOGGER.info('Salt Bridges are replaced')

    def setNewRepulsiveIonicBonding(self, interaction):
        """Replace default calculation of repulsive ionic bonding by the one provided by user"""

        self._interactions[2] = interaction
        self._rib = self._interactions[2]   
        LOGGER.info('Repulsive Ionic Bonding are replaced')
        
    def setNewPiStacking(self, interaction):
        """Replace default calculation of pi-stacking interactions by the one provided by user"""

        self._interactions[3] = interaction
        self._piStack = self._interactions[3]   
        LOGGER.info('Pi-Stacking interactions are replaced')

    def setNewPiCation(self, interaction):
        """Replace default calculation of pi-cation interactions by the one provided by user"""

        self._interactions[4] = interaction
        self._piCat = self._interactions[4]   
        LOGGER.info('Pi-Cation interactions are replaced')

    def setNewHydrophobic(self, interaction):
        """Replace default calculation of hydrophobic interactions by the one provided by user"""

        self._interactions[5] = interaction
        self._hps = self._interactions[5]  
        LOGGER.info('Hydrophobic interactions are replaced')

    def buildInteractionMatrix(self, **kwargs):
        """Build matrix with protein interactions which is scored as follows:
            (1) Hydrogen bonds (HBs) +2
            (2) Salt Bridges (SBs) +3 (Salt bridges might be included in hydrogen bonds)
            (3) Repulsive Ionic Bonding (RIB) -1 
            (4) Pi stacking interactions (PiStack) +3
            (5) Pi-cation interactions (PiCat) +3
            (6) Hydrophobic interactions (HPh) +1
                 
        :arg HBs: score per single hydrogen bond
        :type HBs: int, float

        :arg SBs: score per single salt bridge
        :type SBs: int, float

        :arg RIB: score per single repulsive ionic bonding
        :type RIB: int, float

        :arg PiStack: score per pi-stacking interaction
        :type PiStack: int, float

        :arg PiCat: score per pi-cation interaction
        :type PiCat: int, float

        :arg HPh: score per hydrophobic interaction
        :type HPh: int, float        
        """
        atoms = self._atoms   
        interactions = self._interactions
        
        LOGGER.info('Calculating all interactions')
        InteractionsMap = np.zeros([atoms.select('name CA').numAtoms(),atoms.select('name CA').numAtoms()])
        resIDs = list(atoms.select('name CA').getResnums())
        resChIDs = list(atoms.select('name CA').getChids())
        resIDs_with_resChIDs = list(zip(resIDs, resChIDs))
        
        dic_interactions = {'HBs':'Hydrogen Bonds', 'SBs':'Salt Bridges', 'RIB':'Repulsive Ionic Bonding', 'PiStack':'Pi-stacking interactions', 'PiCat':'Pi-cation interactions', 'HPh':'Hydrophobic interactions'}

        if not 'HBs' in kwargs:
            kwargs['HBs'] = 2
        if not 'SBs' in kwargs:
            kwargs['SBs'] = 3
        if not 'RIB' in kwargs:
            kwargs['RIB'] = -1
        if not 'PiStack' in kwargs:
            kwargs['PiStack'] = 3
        if not 'PiCat' in kwargs:
            kwargs['PiCat'] = 3
        if not 'HPh' in kwargs:
            kwargs['HPh'] = 1            
        
        scoring = [kwargs['HBs'], kwargs['SBs'], kwargs['RIB'], kwargs['PiStack'], kwargs['PiCat'], kwargs['HPh']]        

        LOGGER.info('Following scores will be used:')        
        for key,value in kwargs.items(): 
            LOGGER.info('{0} = {1}'.format(dic_interactions[key], value))
        
        for nr_i,i in enumerate(interactions):
            if i != []:
                for ii in i: 
                    m1 = resIDs_with_resChIDs.index((int(ii[0][3:]),ii[2]))
                    m2 = resIDs_with_resChIDs.index((int(ii[3][3:]),ii[5]))
                    InteractionsMap[m1][m2] = InteractionsMap[m1][m2] + scoring[nr_i]
        
        self._interactions_matrix = InteractionsMap
        
        return InteractionsMap


    def showInteractions(self, **kwargs):
        """Display protein residues and their number of potential interactions
        with other residues from protein structure.
        """
        
        import numpy as np
        import matplotlib
        import matplotlib.pylab as plt        
        from prody.dynamics.plotting import showAtomicLines
        
        if not hasattr(self, '_interactions_matrix') or self._interactions_matrix is None:
            raise ValueError('Please calculate interactions matrix first')

        interaction_matrix = self._interactions_matrix
        atoms = self._atoms 
        
        freq_contacts_residues = np.sum(interaction_matrix, axis=0)
        ResNumb = atoms.select('protein and name CA').getResnums()
        ResName = atoms.select('protein and name CA').getResnames()
        ResChid = atoms.select('protein and name CA').getChids()

        ResList = [ i[0]+str(i[1])+i[2] for i in list(zip(ResName, ResNumb, ResChid)) ]
        
        matplotlib.rcParams['font.size'] = '20' 
        fig = plt.figure(num=None, figsize=(12,6), facecolor='w')
        showAtomicLines(freq_contacts_residues, atoms=atoms.select('name CA'), **kwargs)
        plt.ylabel('Score of interactions')
        plt.xlabel('Residue')
        plt.tight_layout()
        plt.show()
        
    
    def saveInteractionsPDB(self, **kwargs):
        """Save the number of potential interactions to PDB file in occupancy column.
        
        :arg filename: name of the PDB file which will be saved for visualization,
                     it will contain the results in occupancy column.
        :type filename: str
        """
        
        if not hasattr(self, '_interactions_matrix') or self._interactions_matrix is None:
            raise ValueError('Please calculate interactions matrix first')

        import numpy as np
        interaction_matrix = self._interactions_matrix
        atoms = self._atoms     
        freq_contacts_residues = np.sum(interaction_matrix, axis=0)
        
        try:
            from collections import Counter
            lista_ext = []
            atoms = atoms.select("all and noh")
            aa_counter = Counter(atoms.getResindices())
            calphas = atoms.select('name CA')
            for i in range(calphas.numAtoms()):
                lista_ext.extend(list(aa_counter.values())[i]*[round(freq_contacts_residues[i], 8)])
            
            kw = {'occupancy': lista_ext}
            if 'filename' in kwargs:
                writePDB(kwargs['filename'], atoms, **kw)  
                LOGGER.info('PDB file saved.')
            else:
                writePDB('filename', atoms, **kw)
                LOGGER.info('PDB file saved.')
        except: LOGGER.info('There is a problem.')
        

    def getFrequentInteractions(self, contacts_min=3):
        """Provide a list of residues with the most frequent interactions based on the following interactions:
            (1) Hydrogen bonds (hb)
            (2) Salt Bridges (sb)
            (3) Repulsive Ionic Bonding (rb) 
            (4) Pi stacking interactions (ps)
            (5) Pi-cation interactions (pc)
            (6) Hydrophobic interactions (hp)
        
        :arg contacts_min: Minimal number of contacts which residue may form with other residues. 
        :type contacts_min: int, be default 3.  """

        atoms = self._atoms   
        interactions = self._interactions
        
        InteractionsMap = np.empty([atoms.select('name CA').numAtoms(),atoms.select('name CA').numAtoms()], dtype='S256')
        resIDs = list(atoms.select('name CA').getResnums())
        resChIDs = list(atoms.select('name CA').getChids())
        resIDs_with_resChIDs = list(zip(resIDs, resChIDs))
        interaction_type = ['hb','sb','rb','ps','pc','hp']

        for nr,i in enumerate(interactions):
            if i != []:
                for ii in i: 
                    m1 = resIDs_with_resChIDs.index((int(ii[0][3:]),ii[2]))
                    m2 = resIDs_with_resChIDs.index((int(ii[3][3:]),ii[5]))
                    InteractionsMap[m1][m2] = interaction_type[nr]+':'+ii[0]+ii[2]+'-'+ii[3]+ii[5]
        InteractionsMap = InteractionsMap.astype(str)

        ListOfInteractions = [ list(filter(None, InteractionsMap[:,j])) for j in range(len(interactions[0])) ]
        ListOfInteractions = list(filter(lambda x : x != [], ListOfInteractions))
        ListOfInteractions = [k for k in ListOfInteractions if len(k) >= contacts_min ]
        ListOfInteractions_list = [ (i[0].split('-')[-1], [ j.split('-')[0] for j in i]) for i in ListOfInteractions ]
        LOGGER.info('The most frequent interactions between:')
        for res in ListOfInteractions_list:
            LOGGER.info('{0}  <--->  {1}'.format(res[0], '  '.join(res[1])))

        LOGGER.info('Legend: hb-hydrogen bond, sb-salt bridge, rb-repulsive ionic bond, ps-Pi stacking interaction,'
                                                    ' pc-Cation-Pi interaction, hp-hydrophobic interaction')
        
        try:
            from toolz.curried import count
        except ImportError:
            LOGGER.warn('This function requires the module toolz')
            return
        
        LOGGER.info('The biggest number of interactions: {}'.format(max(map(count, ListOfInteractions))))
        
        return ListOfInteractions_list
        

    def showFrequentInteractions(self, cutoff=5, **kwargs):
        """Plots regions with the most frequent interactions.
        
        :arg cutoff: minimal score per residue which will be displayed.
                     If cutoff value is to big, top 30% with the higest values will be returned.
        :type distA: int, float
        
        Nonstandard resiudes can be updated in a following way:
        d = {'CYX': 'X', 'CEA': 'Z'}
        >>> name.showFrequentInteractions(d)
        """
        
        if not hasattr(self, '_interactions_matrix') or self._interactions_matrix is None:
            raise ValueError('Please calculate interactions matrix first')

        import numpy as np
        import matplotlib
        import matplotlib.pyplot as plt
        
        atoms = self._atoms
        interaction_matrix = self._interactions_matrix        
        
        aa_dic = {'CYS': 'C', 'ASP': 'D', 'SER': 'S', 'GLN': 'Q', 'LYS': 'K',
             'ILE': 'I', 'PRO': 'P', 'THR': 'T', 'PHE': 'F', 'ASN': 'N', 
                  'GLY': 'G', 'HIS': 'H', 'LEU': 'L', 'ARG': 'R', 'TRP': 'W', 
                       'ALA': 'A', 'VAL':'V', 'GLU': 'E', 'TYR': 'Y', 'MET': 'M', 'HSE': 'H', 'HSD': 'H'}#, **kwargs}

        for key, value in kwargs.items():
            aa_dict[key] = value

        freq_contacts_residues = np.sum(interaction_matrix, axis=0)
        ResNumb = atoms.select('protein and name CA').getResnums()
        ResName = atoms.select('protein and name CA').getResnames()
        ResChid = atoms.select('protein and name CA').getChids()
        ResList = [ i[0]+str(i[1])+i[2] for i in list(zip(ResName, ResNumb, ResChid)) ]

        all_y = [ aa_dic[i[:3]]+i[3:] for i in  ResList]

        if cutoff > np.max(freq_contacts_residues):
            cutoff = round(np.max(freq_contacts_residues)*0.7)

        y = []
        x = []
        for nr_ii, ii in enumerate(freq_contacts_residues):
            if ii >= cutoff:
                x.append(ii)
                y.append(all_y[nr_ii])

        matplotlib.rcParams['font.size'] = '20' 
        fig = plt.figure(num=None, figsize=(12,6), facecolor='w')
        y_pos = np.arange(len(y))
        
        plt.bar(y_pos, x, align='center', alpha=0.5, color='blue', **kwargs)
        plt.xticks(y_pos, y, rotation=45, fontsize=20)
        plt.ylabel('Score of interactions')
        plt.tight_layout()
        plt.show()
        
        
class InteractionsDCD(object):

    """Class for Interaction analysis of DCD trajectory."""

    def __init__(self, name='Unknown'):
        
        self._atoms = None
        self._dcd = None
        self._interactions_dcd = None
        self._interactions_nb_dcd = None
        self._interactions_matrix_dcd = None
        self._hbs_dcd = None
        self._sbs_dcd = None
        self._rib_dcd = None
        self._piStack_dcd = None
        self._piCat_dcd = None
        self._hps_dcd = None


    def calcProteinInteractionsDCD(self, atoms, trajectory, filename=None, **kwargs):
        """Compute all protein interactions (shown below) for DCD trajectory using default parameters.
            (1) Hydrogen bonds
            (2) Salt Bridges
            (3) RepulsiveIonicBonding 
            (4) Pi stacking interactions
            (5) Pi-cation interactions
            (6) Hydrophobic interactions
        
        :arg atoms: an Atomic object from which residues are selected
        :type atoms: :class:`.Atomic`
        
        :arg trajectory: trajectory file
        :type trajectory: class:`.Trajectory`        

        :arg filename: Name of pkl filename in which interactions will be storage
        :type filename: pkl """

        try:
            coords = (atoms._getCoords() if hasattr(atoms, '_getCoords') else
                        atoms.getCoords())
        except AttributeError:
            try:
                checkCoords(coords)
            except TypeError:
                raise TypeError('coords must be an object '
                                'with `getCoords` method')
        
        if not isinstance(trajectory, (TrajBase, Ensemble, Atomic)):
            raise TypeError('{0} is not a valid type for trajectory'
                        .format(type(trajectory)))

        if isinstance(trajectory, Atomic):
            trajectory = Ensemble(trajectory)
                        
        HBs_all = []
        SBs_all = []
        RIB_all = []
        PiStack_all = []
        PiCat_all = []
        HPh_all = []

        HBs_nb = []
        SBs_nb = []
        RIB_nb = []
        PiStack_nb = []
        PiCat_nb = []
        HPh_nb = []
        trajectory.reset()
        
        for j0, frame0 in enumerate(trajectory):  
            LOGGER.info('Frame: {0}'.format(j0))
            
            hydrogen_bonds = calcHydrogenBonds(atoms.protein, **kwargs)
            salt_bridges = calcSaltBridges(atoms.protein, **kwargs)
            RepulsiveIonicBonding = calcRepulsiveIonicBonding(atoms.protein, **kwargs)
            Pi_stacking = calcPiStacking(atoms.protein, **kwargs)
            Pi_cation = calcPiCation(atoms.protein, **kwargs)
            hydrophobic = calcHydrophobic(atoms.protein, **kwargs)

            HBs_all.append(hydrogen_bonds)
            SBs_all.append(salt_bridges)
            RIB_all.append(RepulsiveIonicBonding)
            PiStack_all.append(Pi_stacking)
            PiCat_all.append(Pi_cation)
            HPh_all.append(hydrophobic)
            
            HBs_nb.append(len(hydrogen_bonds))
            SBs_nb.append(len(salt_bridges))
            RIB_nb.append(len(RepulsiveIonicBonding))
            PiStack_nb.append(len(Pi_stacking))
            PiCat_nb.append(len(Pi_cation))
            HPh_nb.append(len(hydrophobic))
        
        self._atoms = atoms
        self._dcd = trajectory
        self._interactions_dcd = [HBs_all, SBs_all, RIB_all, PiStack_all, PiCat_all, HPh_all]
        self._interactions_nb_dcd = [HBs_nb, SBs_nb, RIB_nb, PiStack_nb, PiCat_nb, HPh_nb]
        self._hbs_dcd = HBs_all
        self._sbs_dcd = SBs_all  
        self._rib_dcd = RIB_all
        self._piStack_dcd = PiStack_all
        self._piCat_dcd = PiCat_all
        self._hps_dcd = HPh_all
        
        if filename is not None:
            import pickle
            with open(str(filename)+'.pkl', 'wb') as f:
                pickle.dump(self._interactions_dcd, f)  
            LOGGER.info('File with interactions saved.')
        else: pass
            
        return HBs_nb, SBs_nb, RIB_nb, PiStack_nb, PiCat_nb, HPh_nb


    def getInteractions(self, **kwargs):
        """Return the list of all interactions"""
        
        if 'filename' in kwargs:

            with open(kwargs['filename']+'.dat', 'wb') as f:
                pickle.dump(self._interactions_dcd, f)  
            LOGGER.info('File with interactions saved.')
        else: pass
        
        return self._interactions_dcd

    def getAtoms(self):
        """Returns associated atoms"""

        return self._atoms
    
    def getInteractionsNumber(self):
        """Return the number of interactions in each frame"""
        
        return self._interactions_nb_dcd 
    
    def getHydrogenBonds(self):
        """Return the list of hydrogen bonds computed from DCD trajectory"""

        return self._hbs_dcd
        
    def getSaltBridges(self):
        """Return the list of salt bridges computed from DCD trajectory"""
        
        return self._sbs_dcd

    def getRepulsiveIonicBonding(self):
        """Return the list of repulsive ionic bonding computed from DCD trajectory"""
        
        return self._rib_dcd
        
    def getPiStacking(self):
        """Return the list of Pi-stacking interactions computed from DCD trajectory"""
        
        return self._piStack_dcd

    def getPiCation(self):
        """Return the list of Pi-cation interactions computed from DCD trajectory"""
        
        return self._piCat_dcd
        
    def getHydrophobic(self):
        """Return the list of hydrophobic interactions computed from DCD trajectory"""
        
        return self._hps_dcd

    def setNewHydrogenBondsDCD(self, interaction):
        """Replace default calculation of hydrogen bonds by the one provided by user"""

        self._interactions_dcd[0] = interaction
        self._hbs_dcd = self._interactions_dcd[0]    
        self._interactions_nb_dcd[0] = [ len(i) for i in interaction ]
        LOGGER.info('Hydrogen Bonds are replaced')

    def setNewSaltBridgesDCD(self, interaction):
        """Replace default calculation of salt bridges by the one provided by user"""

        self._interactions_dcd[1] = interaction
        self._sbs_dcd = self._interactions_dcd[1]  
        self._interactions_nb_dcd[1] = [ len(i) for i in interaction ]
        LOGGER.info('Salt Bridges are replaced')

    def setNewRepulsiveIonicBondingDCD(self, interaction):
        """Replace default calculation of repulsive ionic bonding by the one provided by user"""

        self._interactions_dcd[2] = interaction
        self._rib_dcd = self._interactions_dcd[2]   
        self._interactions_nb_dcd[2] = [ len(i) for i in interaction ]
        LOGGER.info('Repulsive Ionic Bonding are replaced')
        
    def setNewPiStackingDCD(self, interaction):
        """Replace default calculation of pi-stacking interactions by the one provided by user"""

        self._interactions_dcd[3] = interaction
        self._piStack_dcd = self._interactions_dcd[3]   
        self._interactions_nb_dcd[3] = [ len(i) for i in interaction ]
        LOGGER.info('Pi-Stacking interactions are replaced')

    def setNewPiCationDCD(self, interaction):
        """Replace default calculation of pi-cation interactions by the one provided by user"""

        self._interactions_dcd[4] = interaction
        self._piCat_dcd = self._interactions_dcd[4]   
        self._interactions_nb_dcd[4] = [ len(i) for i in interaction ]
        LOGGER.info('Pi-Cation interactions are replaced')

    def setNewHydrophobicDCD(self, interaction):
        """Replace default calculation of hydrophobic interactions by the one provided by user"""

        self._interactions_dcd[5] = interaction
        self._hps_dcd = self._interactions_dcd[5]  
        self._interactions_nb_dcd[5] = [ len(i) for i in interaction ]
        LOGGER.info('Hydrophobic interactions are replaced')
    
    def parseInteractions(self, filename):
        """Import interactions from analysis of trajectory which was saved via
        calcProteinInteractionsDCD().
        
        :arg filename: Name of pkl file in which interactions will be storage
        :type filename: pkl"""
        
        import pickle
        with open(filename, 'rb') as f:
            data = pickle.load(f)
        
        self._interactions_dcd = data
        self._interactions_nb_dcd = [[len(sublist) if sublist else 0 for sublist in sublist] for sublist in data]
        self._hbs_dcd = data[0]
        self._sbs_dcd = data[1]
        self._rib_dcd = data[2]
        self._piStack_dcd = data[3]
        self._piCat_dcd = data[4]
        self._hps_dcd = data[5]
        
        return data
    
    def getTimeInteractions(self, **kwargs):    
        """Return a bar plots with the number of interactions per each frame """
        
        HBs = self._interactions_nb_dcd[0]
        SBs = self._interactions_nb_dcd[1]
        RIB = self._interactions_nb_dcd[2]
        PiStack = self._interactions_nb_dcd[3]
        PiCat = self._interactions_nb_dcd[4]
        HPh = self._interactions_nb_dcd[5]
        
        import numpy as np
        import matplotlib
        import matplotlib.pyplot as plt
        matplotlib.rcParams['font.size'] = '20' 

        fig, (ax1, ax2, ax3, ax4, ax5, ax6) = plt.subplots(6, num=None, figsize=(12,8), facecolor='w', sharex='all', **kwargs)
        hspace = 0.1
        plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=0.35)
        ax1.bar(np.arange(len(HBs)), HBs, color='deepskyblue')
        ax2.bar(np.arange(len(SBs)),SBs, color='yellow')
        ax3.bar(np.arange(len(HPh)), HPh, color='silver')
        ax4.bar(np.arange(len(PiStack)), PiStack, color='lightgreen')
        ax5.bar(np.arange(len(PiCat)), PiCat, color='orange')
        ax6.bar(np.arange(len(RIB)), RIB, color='red')

        ax1.plot(HBs, 'k:')
        ax2.plot(SBs, 'k:')
        ax3.plot(HPh, 'k:')
        ax4.plot(PiStack, 'k:')
        ax5.plot(PiCat, 'k:')
        ax6.plot(RIB, 'k:')

        plt.xlabel('Frame')
        plt.show()   
        
        return HBs, SBs, HPh, PiStack, PiCat, HPh

