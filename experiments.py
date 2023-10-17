import os
import subprocess
import sys
import time
import shutil
import multiprocessing
from multiprocessing import Pool

# Pass in the folder containing the apks and the output folder
apk_folder = os.path.abspath(sys.argv[1])
output_folder = os.path.abspath(sys.argv[2])
tool_name = sys.argv[3] if len(sys.argv) > 3 else "ape"
f = None

#TIMEOUT_LIMIT = 86400
api = 23
#default_avd = "Recent_AVD"
default_avd = f"API{api}_AVD"
#default_avd = "API23_AVD"
instances = 6

avd_availability_queue = multiprocessing.Manager().Queue()
message_queue = multiprocessing.Manager().Queue()


def message_writer(message_queue):
    print("Starting message watcher")
    with open(f"{output_folder}/run_stats.txt", "a+") as stats_file:
        print(f"Writing executed apps to {output_folder}/run_stats.txt")
        while True:
            message = message_queue.get()
            if message == 'kill':
                #stats_file.write('Killed')
                stats_file.close()
                break
            stats_file.write(message)
            stats_file.flush()
            #print(f"Writing executed log to {out_dir}/exec_log.txt")


def get_available_avd(index):
    avd = default_avd + ("" if index == 1 else f"{index}")
    print(f"{avd}")
    return avd


def update_available_avds(id):
    global avd_availability_queue
    global message_queue
    avd_availability_queue.put(id)
    print(f"Making id {id} available, list {avd_availability_queue.qsize()}")
    

def run_experiment(path, app_name, avd_avail_queue, message_queue):

    # Run themis explorer
    # python3 themis.py --avd Recent_AVD4 --apk /data/faridah/apks/googleplay/TopMay2023/Audible_3.50.0_apkcombo.com.apk --time 2h -o ../ape-results/ --ape --offset 3


    print(f"Launching run of {tool_name} for {app_name}")
    message_queue.put(f"Launching run of {tool_name} for {app_name}\n")

    # Get avd index
    avd_index = avd_avail_queue.get()

    # Get output files
    std_err_file = open(f"{output_folder}/errors/{tool_name}_err_log_{app_name}.txt", "a+")
    std_out_file = open(f"{output_folder}/logs/{tool_name}_log_{app_name}.txt", "a+")

    #todo VERSION WITH login
    # if app.hasLogin script, run 1h-2h else run 3h, different names for the files also (or append)
    #todo cold boot?
    cmd = ['python3', 'themis.py', "--avd", get_available_avd(avd_index), "--apk", path, "--time", "2h", "-o", output_folder, f"--{tool_name}", "--offset", f"{avd_index}"]
    print(f"Executing {cmd}")
    start_time = time.time()
    p = subprocess.Popen(cmd, cwd=f"{os.getcwd()}/themis/scripts/", stdout=std_out_file, stderr=std_err_file)
    p.wait()
    end_time = time.time()
    duration = end_time - start_time
    print(f"Done exploring app {app_name}")

    #TODO get num act
    act = 1
    message_queue.put(f"Explored app {app_name} for {duration} \n")

    std_err_file.close()
    std_out_file.close()
    return avd_index

def main():
   
    try:
        print(f"Running on files within directory {apk_folder}")
        print(f"Output directory: {output_folder}")

        #TODO with login, without login
        apk_paths = [f"{apk_folder}/{f}" for f in os.listdir(apk_folder)]
        #apk_paths = sorted(apk_paths, key= lambda x : os.stat(x).st_size)

        pool = Pool(processes=(instances))
        for id in range(1,instances):
                update_available_avds(id)
        #update_available_avds(1)
        watcher = pool.apply_async(message_writer, (message_queue,))
        results = []

        if not os.path.isdir(f"{output_folder}/errors"):
            os.mkdir(f"{output_folder}/errors")

        if not os.path.isdir(f"{output_folder}/logs"):
            os.mkdir(f"{output_folder}/logs")

        for path in apk_paths:
            if path.endswith('.apk'):
                file_name = os.path.basename(path)
                app_name = file_name[:-4]
                
                if os.path.isdir(f"{output_folder}/{app_name}"): #TODO or log file exists?
                    print(f"Skipping {app_name}, already computed")
                    continue

                res = pool.apply_async(run_experiment, args=(path, app_name, avd_availability_queue, message_queue), callback=update_available_avds)
                results.append(res)

        print(f"Need to wait for the results, {len(results)} left")
        [res.get() for res in results]
        print("Waited for all to finish")
        message_queue.put('kill')
        pool.close()
        pool.join()
        print('Complete')
    except Exception as e:
        print("Some kind of exception occured: %s", e)
    finally:
        print("End of script")


if __name__ == '__main__':
    main()