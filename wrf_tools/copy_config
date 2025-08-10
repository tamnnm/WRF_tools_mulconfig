#!/bin/bash
#SBATCH --job-name=submit_namelist
#SBATCH --output=report/submit_namelist.out
#SBATCH --error=report/submit_namelist.err
#SBATCH --time=10-00:00:00
#SBATCH --nodes=1
#SBATCH --exclusive

echo "Please update the developement for region scheme: UAE/Vietnam/ASEAN/Tropical cyclone"
source /home/tamnnm/load_func_vars.sh

usage() {
  echo "Usage: $0 -dataset <DATASET> -ym <YYYYMM> [--last_day <YYYY-MM-DD>] [--check <y|n>]"
  echo "Options:"
  echo "  -dataset <DATASET>   Specify the dataset (e.g., cera, era, era5, noaa)"
  echo "  -ym <YYYYMM>        Specify the year and month (e.g., 202301)"
  echo "  --last_day <YYYY-MM-DD>  Specify the last day (optional)"
  echo "  --check <y|n>       Check the namelist only (optional, default: y)"
  
  exit 1
}

check="y"

# Parse command-line options
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -dataset)
            dataset="$2"
            shift 2
            ;;
        -ym)
            year_month="$2"
            shift 2
            ;;
        --last_day)
            last_day="$2"
            shift 2
            ;;
        --check)
            check="$2"
            shift 2
            ;;
        *)
            echo "Invalid option: $1"
            usage
            ;;
    esac
done

# Check if dataset and year_month are provided
if [ -z "$dataset" ] || [ -z "$year_month" ]; then
  usage
fi

mp_scheme=( 6 8 )
bl_scheme=( 1 2 5 )
sf_scheme=( 1 2 5 )
cu_scheme=( 1 16 )
# Maybe sensitivity test for UAE (4 is a scheme accounted for aerosol - dust for UAE)
#? 24 is the same scheme as 4 but without aerosol
# ra_lw_scheme=( 4 )
# ra_sw_scheme=( 1 4 24 )
ra_sw_scheme=( 1 4 )


wps_path="${wps}/WPS_${dataset}_${year_month}"
root_folder="${dataset}_${year_month}"
prod_folder="${prod_wrf}/wrf_${year_month}"
scheme_log="${prod_folder}/scheme_log.txt"
old_scheme_log="${prod_folder}/old_scheme_log.txt"

# Find the last input file
if [ -z "$last_day" ]; then
    last_infile=$(ls "${wps_path}" | grep "^met_em.d01" | sort | tail -n 1)
    last_day=$(echo $last_infile | cut -d'.' -f3 | cut -d'_' -f1)
    
    sub_infile=$(ls "${wps_path}" | grep "^met_em.d01" | sort | tail -n 2 | head -n 1)
    sub_last_day=$(echo $last_infile | cut -d'.' -f3 | cut -d'_' -f1)
fi

last_outfile="wrfout_d01_${last_day}"
sub_last_outfile="wrfout_d01_${sub_last_day}"

year_month_day(){
  local infile="$1"
  local datetime=$(echo "$infile" | cut -d'.' -f3)
  local year=$(echo "$datetime" | cut -d'-' -f1)
  local month=$(echo "$datetime" | cut -d'-' -f2)
  local day=$(echo "$datetime" | cut -d'-' -f3 | cut -d'_' -f1)
  local hour=$(echo "$datetime" | cut -d'_' -f2 | cut -d':' -f1)
}

create_root_folder() {
  last_infile=$(ls "$wps_path" | grep "^met_em.d01" | sort | tail -n 1)
  first_infile=$(ls "$wps_path" | grep "^met_em.d01" | sort | head -n 1)
  re_infile=$(echo "$last_infile" | sed 's/_00:/_01:/')

  local start_time start_year start_month start_day start_hour
  read start_time start_year start_month start_day start_hour <<< "$(year_month_day ${first_infile})"
  read end_time end_year end_month end_day end_hour <<< "$(year_month_day ${last_infile})"


  if [ ! -d "${prod_folder}" ]; then
    mkdir -p "${prod_folder}"
  fi
  
  # CREATE THE ROOT FOLDER IF NEEDED
  # Check if the root folder exists and edited
  if [ -d "${root_folder}" ]; then
    return
  # If the root folder is created by not edited
  elif [ ! -d "${root_folder}_temp" ]; then
    cp -n -r "EXAMPLE/" "${root_folder}_temp"
  fi

  # EDIT THE ROOT FOLDER
  cd "${root_folder}_temp"
  
  # Clean the folder if needed
  rm -f met_em*
  rm -f rsl*

  rm -f wrfbdy*
  rm -f wrfinput*
  
  # Link the met_em files
  ln -rsf $wps_path/met_em* .

  check_line_input "start_year" "$start_year"
  check_line_input "start_month" "$start_month"
  check_line_input "start_day" "$start_day"
  check_line_input "start_hour" "$start_hour"

  check_line_input "end_year" "$end_year"
  check_line_input "end_month" "$end_month"
  check_line_input "end_day" "$end_day"
  check_line_input "end_hour" "$end_hour"

  check_line_input "restart_interval" "1440"
  check_line_input "adjust_output_times" ".true."
  
  # echo $start_year $start_month $start_day $start_hour
  
  # Edit the area (if needed)
  echo "Opening namelist.wps"
  echo
  head -n 30 $wps_path/namelist.wps
  
  echo
  echo "Opening namelist.input"
  head -n 25 namelist.input
  
  while true; do
    echo "Do you want to modify the nested area (y/n)?"
    read -r modify_area
    if [[ "$modify_area" == "y" ]]; then
      echo "Opening namelist.wps"
      sleep 7
      vi namelist.wps
      break
    elif [[ "$modify_area" == "n" ]]; then
      echo "Skipping the modification of the nested area"
      sleep 7
      break
    else
      echo "Invalid input. Please enter 'y' or 'n'."
    fi
  done
  
  # Format the namelist.input
  formatted_namelist "namelist.input"
  cd ..
  
  # ARCHIVE THE ROOT FOLDER
  mv "${wrf_test}/${root_folder}_temp" "${wrf_test}/${root_folder}"
  cp namelist.input "${prod_folder}/org_namelist.input"
}

check_sub_folder(){
  local number=$1
  
  ind_base_folder="${root_folder}_${number}"
  prod_ind_folder="${prod_folder}/${root_folder}_${number}"
  
  if ls "$last_outfile"* 1> /dev/null 2>&1 || ls "$prod_ind_folder/$last_outfile"* 1> /dev/null 2>&1; then
    echo "WRF for $ind_base_folder has already been run."
    echo
    
    if [ -d "${ind_base_folder}" ]; then
      echo "Archiving the base folder....."
      mv "${ind_base_folder}" "/work/users/tamnnm/trashbin/WRF_archive/"
      echo
    fi
    
    return
  fi
  
  if [ ! -d "${root_folder}" ]; then
    echo "The root folder is not completely edited"
    exit 1
  fi
  
  if [ ! -d "${ind_base_folder}" ]; then
    echo "$ind_base_folder does not exist"
  fi
  
  echo "$ind_base_folder existed"
}

create_sub_folder(){
  local number=$1
  local mp_scheme=$2
  local bl_scheme=$3
  local sf_scheme=$4
  local cu_scheme=$5
  local ra_sw_scheme=$6
  # local ra_lw_scheme=$7

  ind_base_folder="${root_folder}_${number}"
  prod_ind_folder="${prod_folder}/${root_folder}_${number}"
  
  # Condition to skip completed cases
  if ls "$last_outfile"* 1> /dev/null 2>&1 || ls "$prod_ind_folder/$last_outfile"* 1> /dev/null 2>&1; then
    echo "WRF for $ind_base_folder has already been run."
    echo
    
    if [ -d "${ind_base_folder}" ]; then
      echo "Archiving the base folder....."
      mv "${ind_base_folder}" "/work/users/tamnnm/trashbin/WRF_archive/"
      echo
    fi
    
    return
  fi
  
  if [ ! -d "${root_folder}" ]; then
    echo "The root folder is not completely edited"
    exit 1
  fi
  
  if [ ! -d "${ind_base_folder}" ]; then
    echo "Creating sub-folder for $ind_base_folder"
    cp -n -r "${root_folder}" "${ind_base_folder}"
  fi
  
  job_exists "$ind_base_folder"
  wrf_job_exists=$?
  if [ $wrf_job_exists -eq 0 ]; then
      echo "Job with name '$ind_base_folder' is already in the queue."
      # Complete one folder
      check_id=$((check_id+1))
      return
  fi
  
  if [ ! -d "${prod_ind_folder}" ]; then
    mkdir ${prod_ind_folder}
  fi
  
  echo "Editing sub_folder for $ind_base_folder"
  
  # -------------------------- RESTART CHECK ------------------------- #
  # Check the restart file of the last run
  #   1. If the last run is the first run => Re_run
  #   2. If the last run > out run => Sub_restart else Last_Restart
  #   3. If the last run created after the out run => Sub_restart else Last_Restart
  #   4. If the last run is the completed run => Skip
  
  # 1st lastest restart file
  last_ind_rst=$(ls $prod_ind_folder | grep "^wrfrst_d01_.*$" | sort | tail -n 1)
  last_ind_out=$(ls $prod_ind_folder | grep "^wrfout_d01_.*00:00:00$" | sort | tail -n 1)
  last_actual_out=$(ls $prod_ind_folder | grep "^wrfout_d01_.*$" | sort | tail -n 1)
  # 2nd lastest restart file
  sub_ind_rst=$(ls $prod_ind_folder | grep "^wrfrst_d01_.*$" | sort | tail -n 2 | head -n 1)
  
  # Default restart flag: False
  restart_flag=1
  
  # Check the last actual outfile
  #? Sometimes, after restart, the name of the last actual outfile is not the same as the last_outfile
  #? You have to check the last actual outfile to make sure
  if [[ (-n "$last_actual_out" && "$last_actual_out" == *"01:00:00") || -n "$sub_ind_rst" ]]; then
    echo "WRF for $ind_base_folder has already been restart at some point. Please check the restart file"
    # print the last restart file
    echo "Last restart file: $last_actual_out"
    cdo sinfo $prod_ind_folder/$last_actual_out
    while true; do
      echo "Do you want to restart the WRF for $ind_base_folder (y/n)?"
      read -r restart_option
      if [[ "$restart_option" == "n" ]]; then
        return
      elif [[ "$restart_option" == "y" ]]; then
        last_ind_out=$last_actual_out
        break
      else
        echo "Invalid input. Please enter 'y' or 'n'."
      fi
    done
  fi
  
  if [ -n "$last_ind_rst" ] ; then
    rst_creation_time=$(stat -c %Y "$prod_ind_folder/$last_ind_rst")
    out_creation_time=$(stat -c %Y "$prod_ind_folder/$last_ind_out")
    
    rst_datetime=$(echo "$last_ind_rst" | awk -F'_' '{print $3}')
    out_datetime=$(echo "$last_ind_out" | awk -F'_' '{print $3}')
    sub_rst_datetime=$(echo "$sub_ind_rst" | awk -F'_' '{print $3}')
    
    # Compare the date of wrf_rst and wrf_out
    if [ $(date -d "$rst_datetime" +%Y%m%d) -gt $(date -d "$out_datetime" +%Y%m%d) ]; then
        # If the last_ind_rst is the only restart file => Re_run
        if [ -n "$sub_rst" ]; then
          rst_datetime=$sub_rst_datetime
          last_ind_rst=$sub_ind_rst
          restart_flag=0
        fi
    else
    # Compare the creation time of wrf_rst and wrf_out
        if [ "$rst_creation_time" -gt "$out_creation_time" ]; then
        # Second test: The restart is broken => Choose the sub_rst
            if [ -n "$sub_rst" ]; then
              rst_datetime=$sub_rst_datetime
              last_ind_rst=$sub_ind_rst
              restart_flag=0
            fi
        fi
    fi
  fi
  
  cd "${ind_base_folder}"

  rm -f met_em*
  ln -rsf $wps_path/met_em* .
  
  # Copy the namelist.input from the root folder (overwrite the existing one)
  mv "namelist.input" "old_namelist.input"
  cp "../${root_folder}/namelist.input" "namelist.input"
  
  # --------------------- EDIT THE NAMELIST.INPUT -------------------- #
  check_line_input "history_outname" "${prod_ind_folder}/wrfout_d<domain>_<date>"
  check_line_input "rst_outname" "${prod_ind_folder}/wrfrst_d<domain>_<date>"
  check_line_input "mp_physics" "${mp_scheme}"
  check_line_input "bl_pbl_physics" "${bl_scheme}"
  check_line_input "sf_sfclay_physics" "${sf_scheme}"
  check_line_input "cu_physics" "${cu_scheme}"
  # check_line_input "ra_lw_physics" "${ra_scheme}"
  check_line_input "ra_lw_physics" "4"
  check_line_input "ra_sw_physics" "${ra_sw_scheme}"
  
  if [[ $cu_scheme != 1 ]]; then
    check_line_input "cu_rad_feedback" ".false."
  fi
  
  formatted_namelist "namelist.input"
  
  # Archive the namelist.input in the prod_ind_folder
  cp "namelist.input" "${prod_ind_folder}/namelist.input"

  # ------------------------- EDIT TO RESTART ------------------------ #
  # If the restart flag is true, skip the restart
  if [[ $restart_flag -eq 0 ]]; then
    hour_part=$(echo "$last_ind_rst" | awk -F'_' '{print $4}')
    hour=$(echo "$hour_part" | cut -d':' -f1)
    year=$(echo "$rst_datetime" | cut -d'-' -f1)
    month=$(echo "$rst_datetime" | cut -d'-' -f2)
    day=$(echo "$rst_datetime" | cut -d'-' -f3)
    check_line_input "start_year" "$year"
    check_line_input "start_month" "$month"
    check_line_input "start_day" "$day"
    check_line_input "start_hour" "$hour"
    check_line_input "restart" ".true."
    check_line_input "override_restart_timers" ".true."
    
    check_line_input "history_outname" "${prod_ind_folder}/wrfout_d<domain>_<date>"
    check_line_input "rst_outname" "${prod_ind_folder}/wrfrst_d<domain>_<date>"
    echo "Restarting from ${rst_datetime}_${hour_part} for $ind_base_folder"
    
    formatted_namelist "namelist.input"
  
    # Copy the restart file to the sub_folder
    cp -n $prod_ind_folder/wrfrst_d0*_${rst_datetime}_${hour_part} ./
  fi
  
  # GO BACK TO THE TEST FOLDER
  cd ..
}

# Initialize the job number
j=1

# GO TO THE TEST FOLDER
cd "${wrf_test}"

# CREATE THE ROOT FOLDER
create_root_folder

# Record the scheme log
cp $scheme_log $old_scheme_log
> $scheme_log

# Loop through the schemes
for ra_sw in "${ra_sw_scheme[@]}"; do
  for mp in "${mp_scheme[@]}"; do
    for bl in "${bl_scheme[@]}"; do
      for sf in "${sf_scheme[@]}"; do
        for cu in "${cu_scheme[@]}"; do
        
          if [ "$j" -lt 10 ]; then
            no_job="0$j"
          else
            no_job="$j"
          fi

          # Exception for certain scheme
          if { [ "$bl" -eq 1 ] && [ "$sf" -ne 1 ]; } || { [ "$bl" -eq 2 ] && [ "$sf" -ne 2 ]; }; then
            continue
          fi
         
          # UAE scheme
          
          # TODO: Test for re_run and re_start here
          #? Only create sub_folder if suitable
          echo "no_job: ${no_job}, mp_physics: ${mp}, bl_pbl_physics: ${bl}, sf_sfclay_physics: ${sf}, cu_physics: ${cu}, ra_sw_physics: ${ra_sw}, ra_lw_physics: 24" >> $scheme_log
          
          if [ "$check" == "y" ]; then
            check_sub_folder "${no_job}"
          else
            create_sub_folder "${no_job}" "${mp}" "${bl}" "${sf}" "${cu}" "${ra_sw}"
          fi
          
          # Only for testing
          # check_sub_folder "${no_job}"
          
          j=$((j+1))
        done
      done
    done
  done
done
