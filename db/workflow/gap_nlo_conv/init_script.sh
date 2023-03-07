#!/usr/bin/env bash
prefix="m-all-rk9"
job=0
casename="FeS2m"

if [ $# == 1 ];then
    if [ $1 == "sub" ];then
        job="submit"
    elif [ $1 == "s" ];then
        job="script"
    elif [ $1 == "a" ];then
        job="all"
    else
        echo "usage: $0 [sub|s|a]"
        exit 1
    fi
else
    echo "usage: $0 [sub|s|a]"
    exit 2
fi

for p in {0..4}; do
for i in {0..6}
do
    dirhead="nlo${i}p${p}"
    if (( p == 0 )); then
    dirhead="nlo${i}"
    fi
    if [ -d ${dirhead} ];then
        echo "- found ${dirhead}"
	if [ -f  "${dirhead}/$casename.eqpeV_GW0" ]; then
	echo "- calclation done in ${dirhead}, skip"
        continue
        fi
        if [ $job == "script" ];then
            sed "s/JOBNAME/${prefix}-${dirhead}/g" run_gap2.sh > ${dirhead}/run_gap2.sh
	    chmod +x ${dirhead}/run_gap2.sh
        elif [ $job == "submit" ];then
            cd ${dirhead}
            sbatch run_gap2.sh
            cd ..
        elif [ $job == "all" ];then
            sed "s/JOBNAME/${prefix}-${dirhead}/g" run_gap2.sh > ${dirhead}/run_gap2.sh
	    chmod +x ${dirhead}/run_gap2.sh
            cd ${dirhead}
            sbatch run_gap2.sh
            cd ..
        fi
    fi
done
done


