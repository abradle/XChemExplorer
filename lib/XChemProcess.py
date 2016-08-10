# last edited: 09/08/2016, 15:00

import os, sys, glob
from PyQt4 import QtGui, QtCore

sys.path.append(os.path.join(os.getenv('XChemExplorer_DIR'),'lib'))
import XChemLog

class run_xia2(QtCore.QThread):
    def __init__(self,initial_model_directory,run_dict,protocol,spg,ref,xce_logfile,external_software,ccp4_scratch_directory,max_queue_jobs):
        QtCore.QThread.__init__(self)
        self.initial_model_directory=initial_model_directory
        self.run_dict=run_dict
        self.protocol=protocol
        self.spg=spg
        self.ref=ref
        self.xce_logfile=xce_logfile
        self.Logfile=XChemLog.updateLog(xce_logfile)
        self.external_software=external_software
        self.ccp4_scratch_directory=ccp4_scratch_directory
        self.max_queue_jobs=max_queue_jobs

    def run(self):
        os.chdir(os.path.join(self.initial_model_directory))
        # first create directories if they do not exist

        if self.protocol == []:
            self.Logfile.insert('please select data processing protocol first!')
            return None

        for i,xtal in enumerate(self.run_dict):

            script=''

            if self.external_software['qsub']:
                script+='#PBS -joe -N XCE_reprocess\n'
            else:
                script+='#!'+os.getenv('SHELL')+'\n'


            if self.spg == []:
                spg_option=''
            else:
                spg_option='space_group='+str(self.spg[0])

            if self.ref == []:
                ref_option=''
            else:
                ref_option='-reference_reflection_file '+str(self.ref[0])

            # first link diffraction images into directory
            if not os.path.isdir(os.path.join(self.initial_model_directory,xtal)):
                os.mkdir(os.path.join(self.initial_model_directory,xtal))
            if not os.path.isdir(os.path.join(self.initial_model_directory,xtal,'diffraction_images')):
                os.mkdir(os.path.join(self.initial_model_directory,xtal,'diffraction_images'))

            if not os.path.isdir(os.path.join(self.initial_model_directory,xtal,'processed')):
                os.mkdir(os.path.join(self.initial_model_directory,xtal,'processed'))

            if os.path.isfile(os.path.join(self.initial_model_directory,xtal,'processed','run_in_progress')):
                self.Logfile.insert('data processing is in progress; skipping...')
                continue
            else:
                os.chdir(os.path.join(self.initial_model_directory,xtal,'processed'))
                os.system('touch run_in_progress')

            for n,root in enumerate(self.run_dict[xtal]):
                if n==0:
                    datadir=root[0]
                else:
                    if not os.path.isdir(os.path.join(self.initial_model_directory,xtal,'diffraction_images','run_'+str(n))):
                        os.mkdir(os.path.join(self.initial_model_directory,xtal,'diffraction_images','run_'+str(n)))
                    image_dir=os.path.join(self.initial_model_directory,xtal,'diffraction_images','run_'+str(n))
                    os.chdir(os.path.join(self.initial_model_directory,xtal,'diffraction_images','run_'+str(n)))
                    os.system('ln -s '+os.path.join(datadir,root[0])+'* .')

                    os.chdir(os.path.join(self.initial_model_directory,xtal))
                    if not os.path.isdir(os.path.join(self.initial_model_directory,xtal,'processed')):
                        os.mkdir(os.path.join(self.initial_model_directory,xtal,'processed'))
                    if not os.path.isdir(os.path.join(self.initial_model_directory,xtal,'processed','run_'+str(n))):
                        os.mkdir(os.path.join(self.initial_model_directory,xtal,'processed','run_'+str(n)))


                    os.chdir(os.path.join(self.initial_model_directory,xtal,'processed'))
                    os.system('touch run_in_progress')

                    for pipeline in self.protocol:
                        script+='cd '+os.path.join(self.initial_model_directory,xtal,'processed','run_'+str(n),pipeline)+'\n'
                        if not os.path.isdir(os.path.join(self.initial_model_directory,xtal,'processed','run_'+str(n),pipeline)):
                            os.mkdir(os.path.join(self.initial_model_directory,xtal,'processed','run_'+str(n),pipeline))
                        script+='xia2 -'+pipeline+' '+ref_option+' '+spg_option+' '+image_dir+'\n'

            script+='cd '+os.path.join(self.initial_model_directory,xtal,'processed')+'\n'
            script+='/bin/rm run_in_progress\n'

            os.chdir(self.ccp4_scratch_directory)
            f = open('xce_xia2_%s.sh' %str(i+1),'w')
            f.write(script)
            f.close()
            os.system('chmod +x xce_xia2_%s.sh' %str(i+1))

        # submit job
        self.Logfile.insert('created input scripts for '+str(n+1)+' in '+self.ccp4_scratch_directory)
        os.chdir(self.ccp4_scratch_directory)
        if os.getcwd().startswith('/dls'):
            if self.external_software['qsub_array']:
                Cmds = (
                        '#PBS -joe -N xce_xia2_master\n'
                        './xce_xia2_$SGE_TASK_ID.sh\n'
                        )
                f = open('xia2_master.sh','w')
                f.write(Cmds)
                f.close()
                self.Logfile.insert('submitting array job with maximal 100 jobs running on cluster')
                self.Logfile.insert('using the following command:')
                self.Logfile.insert('qsub -t 1:%s -tc %s xia2_master.sh' %(str(i+1),self.max_queue_jobs))
                os.system('qsub -t 1:%s -tc %s xia2_master.sh' %(str(i+1),self.max_queue_jobs))
            else:
                self.Logfile.insert("cannot start ARRAY job: make sure that 'module load global/cluster' is in your .bashrc or .cshrc file")
        elif self.external_software['qsub']:
            self.Logfile.insert('submitting %s individual jobs to cluster' %(str(i+1)))
            self.Logfile.insert('WARNING: this could potentially lead to a crash...')
            for n in range(i+1):
                self.Logfile.insert('qsub xce_xia2_%s.sh' %(str(n+1)))
                os.system('qsub xce_xia2_%s.sh' %(str(n+1)))
        else:
            self.Logfile.insert('running %s consecutive XIA2 jobs on your local machine')
            for n in range(i+1):
                self.Logfile.insert('starting xce_xia2_%s.sh' %(str(n+1)))
                os.system('./xce_xia2_%s.sh' %(str(n+1)))


#            if not os.path.isdir(os.path.join(self.initial_model_directory,xtal)):
#                os.mkdir(os.path.join(self.initial_model_directory,xtal))
#            if not os.path.isdir(os.path.join(self.initial_model_directory,xtal,'autoprocessing')):
#                os.mkdir(os.path.join(self.initial_model_directory,xtal,'autoprocessing'))
#
#
#
#
#            if not os.path.isdir(os.path.join(self.initial_model_directory,xtal,'dimple',visit_run_autoproc)):
#                os.mkdir(os.path.join(self.initial_model_directory,xtal,'dimple',visit_run_autoproc))
#            os.chdir(os.path.join(self.initial_model_directory,xtal,'dimple',visit_run_autoproc))
#            os.system('touch dimple_run_in_progress')




#        header='#!'+os.getenv('SHELL')+'\n'
#        if external_software['qsub']:
#            if not external_software['qsub_array']:
#                header='#PBS -joe -N xce_acedrg\n'
#
#        Cmds = (
#                    header+
#                    '\n'
#                    'export XChemExplorer_DIR="'+os.getenv('XChemExplorer_DIR')+'"\n'
#                    '\n'
#                    'source $XChemExplorer_DIR/setup-scripts/xce.setup-sh\n'
#                    '\n'
#                    '$CCP4/bin/ccp4-python '+os.path.join(os.getenv('XChemExplorer_DIR'),'helpers','create_png_of_compound.py')+
#                    ' "%s" %s %s %s\n' %(smiles,compoundID.replace(' ',''),sample,initial_model_directory)+
#                    '\n'
#                    'cd '+os.path.join(initial_model_directory,sample,'compound')+'\n'
#                    '\n'
#                    'acedrg --res LIG -i "%s" -o %s\n' %(smiles,compoundID.replace(' ',''))+
#                    '\n'
#                    'cd '+os.path.join(initial_model_directory,sample)+'\n'
#                    '\n'
#                    'ln -s compound/%s.cif .\n' %compoundID.replace(' ','')+
#                    'ln -s compound/%s.pdb .\n' %compoundID.replace(' ','')+
#                    'ln -s compound/%s.png .\n' %compoundID.replace(' ','')+
#                    '\n'
#                    '$CCP4/bin/ccp4-python '+os.path.join(os.getenv('XChemExplorer_DIR'),'helpers','update_data_source_for_new_cif_files.py')+
#                    ' %s %s %s %s\n' %(os.path.join(database_directory,data_source_file),sample,initial_model_directory,compoundID.replace(' ','') )+
#                    '\n'
#                    '/bin/rm compound/ACEDRG_IN_PROGRESS\n'