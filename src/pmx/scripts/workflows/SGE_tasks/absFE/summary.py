#!/usr/bin/env python

import copy
import luigi
import os
import numpy as np
#import matplotlib as plt
from luigi.contrib.sge import LocalSGEJobTask
from pmx.scripts.workflows.SGE_tasks.absFE.LinP.analysis import Task_PL_analysis_aligned
from pmx.scripts.workflows.SGE_tasks.absFE.LinW.analysis import Task_WL_analysis_aligned


# ==============================================================================
#                         Derivative Task Classes
# ==============================================================================
class Task_summary_aligned(LocalSGEJobTask):

    #Parameters:
    hosts = luigi.ListParameter(description='list of protein names to evaluate')
    ligands = luigi.ListParameter(description='list of ligand names to evaluate')

    #TODO: add default
    study_settings = luigi.DictParameter(significant=False,
        description='Dict of study stettings '
        'used to propagate settings to dependencies')

    #change default parallel environment
    parallel_env = luigi.Parameter(default='openmp_fast', significant=False)

    #request 1 core
    n_cpu = luigi.IntParameter(default=1, significant=False)

    #avoid Prameter not a string warnings
    job_name_format = luigi.Parameter(
        significant=False, default="pmx_{task_family}",
        description="A string that can be "
        "formatted with class variables to name the job with qsub.")
    job_name = luigi.Parameter(
        significant=False, default="",
        description="Explicit job name given via qsub.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.WL_settings=copy.deepcopy(self.study_settings.get_wrapped())
        self.WL_settings['TIstates']=self.WL_settings['states']
        self.PL_settings=self.study_settings

        self.base_path = self.study_settings['base_path']

    def work(self):

        def read_results():
            rs=np.ndarray(self.study_settings['n_repeats'])
            for i in range(self.study_settings['n_repeats']):
                ana_folder=folder_path+"/analysis/repeat%d"%i
                with open(ana_folder+"/results.txt", 'r') as f:
                    for line in f:
                        if "BAR: dG" in line:
                            s = line.split()
                            rs[i]=float(s[3])
                            break
            dGpart = np.mean(rs)
            std = np.std(rs)
            return([dGpart,std])

        #dG in water
        inws={}
        p="water"
        for l in self.ligands:
            key=l
            folder_path = self.base_path+'/'+p+'/lig_'+l
            inws.update({key:read_results()})

        #dG in protein
        inps={}
        for p in self.hosts:
            for l in self.ligands:
                key=p+' '+l
                folder_path = self.base_path+'/prot_'+p+'/lig_'+l
                inps.update({key:read_results()})

        #read analytical corrections for restraints
        anacorrs={}
        for p in self.hosts:
            for l in self.ligands:
                key=p+' '+l
                folder_path = self.base_path+'/prot_'+p+'/lig_'+l
                with open(folder_path+"/out_dg.dat", 'r') as f:
                    for line in f:
                        if("Restraint contribution to free energy (w gmx limits):" in line and
                           "kJ/mol" in line):
                            s=line.split()
                            anacorrs.update({key:float(s[-2])})


        #print summary table
        with open("summary_aligned.txt", 'w') as sf:

            print("{:^20s} \t{:^20s}   {:^20s}   {:^20s}   {:^12s}".format(
                            "host guest","ddG (kJ/mol)","dG in prot" ,
                            "dG in water", "restraint dG"))
            sf.write("{:^20s} \t{:^20s}   {:^20s}   {:^20s}   {:^12s}\n".format(
                            "host guest","ddG (kJ/mol)","dG in prot" ,
                            "dG in water", "restraint dG"))
            for p in self.hosts:
                for l in self.ligands:
                    key=p+' '+l
                    ddG = inws[l][0] - inps[key][0] - anacorrs[key] #water - protein - restr corr.
                    sigma = np.sqrt(inps[key][1]**2 + inws[l][1]**2) #standard dev.
                    print("{:<20s}:\t{:>8.2f} +- {:<8.2f}   {:>8.2f} +- {:<8.2f}   {:>8.2f} +- {:<8.2f}   {:>12.2f}".format(
                        key, ddG, sigma,
                        inps[key][0], inps[key][1],
                        inws[l][0], inws[l][1],
                        anacorrs[key]) )
                    sf.write("{:<20s}:\t{:>8.2f} +- {:<8.2f}   {:>8.2f} +- {:<8.2f}   {:>8.2f} +- {:<8.2f}   {:>12.2f}\n".format(
                        key, ddG, sigma,
                        inps[key][0], inps[key][1],
                        inws[l][0], inws[l][1],
                        anacorrs[key]) )

    def output(self):
        files=['summary_aligned.txt']
        return([luigi.LocalTarget(os.path.join(self.base_path, f)) for f in files])

    def requires(self):
        tasks=[]

        #Ligand in Water
        p="water"
        for l in self.ligands:
            folder_path = self.base_path+'/'+p+'/lig_'+l
            for sTI in self.WL_settings['states']: #uses equil states for TI
                for i in range(self.WL_settings['n_repeats']):
                    tasks.append(Task_WL_analysis_aligned(
                        l = l, i = i,
                        study_settings = self.WL_settings,
                        folder_path = folder_path,
                        parallel_env=self.parallel_env))

        #Ligand in Protein
        for p in self.hosts:
            for l in self.ligands:
                folder_path = self.base_path+'/prot_'+p+'/lig_'+l
                for sTI in self.PL_settings['TIstates']:
                    for i in range(self.PL_settings['n_repeats']):
                        tasks.append(Task_PL_analysis_aligned(
                            p = p, l = l, i = i,
                            study_settings = self.PL_settings,
                            folder_path = folder_path,
                            parallel_env=self.parallel_env))

        return(tasks)
