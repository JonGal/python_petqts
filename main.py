# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# [START functions_imagemagick_setup]
import os
import tempfile

from google.cloud import storage, vision
from wand.image import Image
from wand.drawing import Drawing


storage_client = storage.Client()
vision_client = vision.ImageAnnotatorClient()
# [END functions_imagemagick_setup]


# [START functions_imagemagick_analyze]
# Blurs uploaded images that are flagged as Adult or Violence.
def blur_offensive_images(data, context):
    file_data = data

    file_name = file_data['name']
    file_base_name = os.path.basename(file_name)
    bucket_name = file_data['bucket']

    blob = storage_client.bucket(bucket_name).get_blob(file_name)
    blob_uri = f'gs://{bucket_name}/{file_name}'
    blob_source = {'source': {'image_uri': blob_uri}}

    # Ignore already-blurred files
    if file_name.startswith('images') :
        print(f'The image {file_name} is already processed.')
        return

    # Ignore already-blurred files
    if file_name.endswith('html') :
        print(f'The image {file_name} is an html file.')
        return


    print(f'Analyzing {file_name}. Base Name: {file_base_name}')

    result = vision_client.safe_search_detection(blob_source)
    detected = result.safe_search_annotation

    # Process image
    if detected.adult == 5 or detected.violence == 5:
        print(f'The image {file_name} was detected as inappropriate.')
        __blur_image(blob)
        file_base_name = "blurred-"+file_base_name
    else:
        storage_client.bucket(bucket_name).rename_blob(blob, "images/"+file_base_name)
        print(f'The image {file_name} was detected as OK.')

    images_blob = storage_client.bucket(bucket_name).get_blob("images/"+file_base_name)
    GenThumbs(images_blob)
    all_thumbs = list(storage_client.bucket(bucket_name).list_blobs(prefix="images/thumb-"))
    UpdatePicts(all_thumbs,storage_client.get_bucket(bucket_name) )

    
# [END functions_imagemagick_analyze]


# [START functions_imagemagick_blur]
# Blurs the given file using ImageMagick.
def __blur_image(current_blob):
    file_name = current_blob.name
    bucket_name = current_blob.bucket
    head_tail = os.path.split(file_name)
    file_base_name = "blurred-" + os.path.basename(head_tail[1])
#    # print head and tail 
#    # of the specified path 
    print(f"Head {head_tail[0]}") 
    print(f"Tail {head_tail[1]}") 
#
    _, temp_local_filename = tempfile.mkstemp()

    # Download file from bucket.
    current_blob.download_to_filename(temp_local_filename)
    print(f'Image {file_name} was downloaded to {temp_local_filename}.')

    # Blur the image using ImageMagick.
    with Image(filename=temp_local_filename) as image:
        image.resize(*image.size, blur=0x24, filter='hamming')
        #image.caption('Inappropriate', left=20, top=50)
        image.save(filename=temp_local_filename)

    print(f'Image {file_name} was blurred.')

    # Upload result to a second bucket, to avoid re-triggering the function.
    # You could instead re-upload it to the same bucket + tell your function
    # to ignore files marked as blurred (e.g. those with a "blurred" prefix)
    #blur_bucket_name = os.getenv('BLURRED_BUCKET_NAME')
    #blur_bucket = storage_client.bucket(blur_bucket_name)

    new_blob_name = "images/"+file_base_name
    new_blob = current_blob.bucket.blob(new_blob_name)
    new_blob.upload_from_filename(temp_local_filename)
    #print(f'Blurred image uploaded to: gs://{blur_bucket_name}/{file_name}')
    print(f'Blurred image uploaded to: gs://{current_blob.bucket}/{new_blob_name}')

    # Delete the temporary file.
    os.remove(temp_local_filename)
# [END functions_imagemagick_blur]

# [START functions_GenThumbs]
def GenThumbs(current_blob):
    file_name = current_blob.name
    bucket_name = current_blob.bucket
    head_tail = os.path.split(file_name)
    file_base_name = "thumb-" + os.path.basename(head_tail[1])
#    # print head and tail 
#    # of the specified path 
    print(f"Head {head_tail[0]}") 
    print(f"Tail {head_tail[1]}") 
#
    _, temp_local_filename = tempfile.mkstemp()

    # Download file from bucket.
    current_blob.download_to_filename(temp_local_filename)
    print(f'Thumbs: Image {file_name} was downloaded to {temp_local_filename}.')

    # Resizw the image using ImageMagick.
    with Image(filename=temp_local_filename) as image:
        image.resize( 234,234)
        #image.caption('Inappropriate', left=20, top=50)
        image.save(filename=temp_local_filename)

    print(f'Image {file_name} was resized.')

    # Upload result to a second bucket, to avoid re-triggering the function.
    # You could instead re-upload it to the same bucket + tell your function
    # to ignore files marked as blurred (e.g. those with a "blurred" prefix)
    #blur_bucket_name = os.getenv('BLURRED_BUCKET_NAME')
    #blur_bucket = storage_client.bucket(blur_bucket_name)

    new_blob_name = "images/"+file_base_name
    new_blob = current_blob.bucket.blob(new_blob_name)
    new_blob.upload_from_filename(temp_local_filename)
    #print(f'Blurred image uploaded to: gs://{blur_bucket_name}/{file_name}')
    print(f'Blurred image uploaded to: gs://{current_blob.bucket}/{new_blob_name}')

    # Delete the temporary file.
    os.remove(temp_local_filename)
# [END functions_GenThumbs]



# [START functions_UpdatePicts]
def UpdatePicts(all_thumbs, current_bucket):
    pictsFile = "picts.html"
    tmpFile = "/tmp/"+pictsFile
    print(f"{tmpFile}")
    fp = open(tmpFile, "w")

    #all_thumbs = list(current_bucket.list_blobs(prefix="images/thumb-"))

    fp.write("<template>\n")

    if(all_thumbs) :
        for obj in all_thumbs:
            fullname = obj.name
            imgname = fullname.replace('thumb-','')
            outStr = "<div class='card'> <a href='"+imgname+"'><img src='http://www.petqts.com/"+fullname+"'  style='height: 280px; width: 100%; display: block;' > </a> </div>\n"
            print(f"{outStr}")
            fp.write(outStr)
    else:
        print(f"No list found of thumbs")

    fp.write("</template>\n")
    fp.close()
            
    new_blob = current_bucket.blob(pictsFile)
    new_blob.upload_from_filename(tmpFile)
# [END functions_UpdatePicts]

