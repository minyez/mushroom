#!/usr/bin/env bash
#SBATCH -A hpc000xxxxxx
#SBATCH --get-user-env
#SBATCH --nodes=1
#SBATCH -n 32
#SBATCH --qos=low
#SBATCH --partition=C032M0256G
#SBATCH -J gw-conv
#SBATCH -o jobid%j-%N.out

# ===== variables =====
# vasp executable
vaspexe="/gpfs/share/home/1501210186/program/vasp.5.4.4/bin/vasp_std"
# number of tasks
defaultnp=4
np=${SLURM_NTASKS:=$defaultnp}
vaspcmd="mpirun -np $np $vaspexe"
# =====================

# need pre-requisites
module load intel/2017.1

# ===== functions =====
backup() {
    cp OUTCAR "OUTCAR.$1"
    cp EIGENVAL "EIGENVAL.$1"
    cp vasprun.xml "vasprun.xml.$1"
}
gw_calc() {
    # 1: step to start. 1 or 2 to skip scf and diag
    # TODO change main stream to make it compatible with 1/2
    doscf=1
    dodiag=1
    if (( $# == 1 ));then
        if (( $1 >= 2 ));then
            doscf=0
        fi
        if (( $1 >= 3 ));then
            dodiag=0
        fi
    fi
    # 1. SCF: compute charge
    if $doscf; then
        cp INCAR.scf INCAR
        cp KPOINTS.scf KPOINTS
        $vaspcmd > out.scf 2>&1
        backup scf
    fi
    # 2. Diagonalization
    if $dodiag;then
        cp INCAR.diag INCAR
        cp KPOINTS.gw KPOINTS
        $vaspcmd > out.diag 2>&1
        backup diag
    fi
    # 3. GW
    cp INCAR.gw INCAR
    $vaspcmd > out.gw 2>&1
    backup gw
    vb=$(awk 'FNR == 21 {print $2}' EIGENVAL)
    cb=$(awk 'FNR == 22 {print $2}' EIGENVAL)
    gap=$(echo "$vb $cb" | awk '{print($2-$1)}')
    etime=$(awk '/Elapsed time/ {print $4}' OUTCAR)
    echo "$gap $etime"
    rm -f ./*.tmp ./WAVE*
}
# =====================

# ===== main =====
if [ ! -f results.txt ];then
  echo "ENCUT  ENCUTGW  NBANDS    Eg   time" > results.txt
fi

for encut in 800 #1000 1270
do
    encutgw=$(echo "$encut 2.0" | awk '{print($1/$2)}')
    nbandsmax=$(echo "$encut 750 1139" | awk '{printf("%d",($1/$2)**1.5 * $3)}')
    for ratio in 0.5 0.6 0.7 0.8 0.9
    do
        nbands=$(echo "$nbandsmax $ratio 192" | awk '{printf("%d",($1*$2) - ($1*$2) % $3)}')
        workdir="encut_${encut}_encutgw_${encutgw}_nbands_${nbands}"
        if [ -d "$workdir" ];then
            continue
        fi
        mkdir -p "$workdir"
        sed "s/_encut_/$encut/g" INCAR.scf  > "$workdir"/INCAR.scf
        sed "s/_encut_/$encut/g;s/_nbands_/$nbands/g" INCAR.diag  > "$workdir"/INCAR.diag
        sed "s/_encut_/ENCUT = $encut/g;s/_nbands_/$nbands/g;s/_encutgw_/$encutgw/g" INCAR.g0w0  > "$workdir"/INCAR.g0w0
        echo -n "$encut $encutgw $nbands  " >> results.txt
        cd "$workdir" || exit 1
        ln -s ../POSCAR POSCAR
        ln -s ../POTCAR POTCAR
        cp ../KPOINTS.dft KPOINTS.dft
        cp ../KPOINTS.gw KPOINTS.gw
        gw_calc 0 >> ../results.txt
        cd ..
    done
done

