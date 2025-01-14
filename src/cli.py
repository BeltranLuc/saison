import click
import os
from src.models.finetuning import make_train_val_folder, make_generator, fit_and_export
from src.data_cleaner import data_vgg_cls, data_seg, data_total, data_vgg_seg
from src.appFlask.models import model
from google.cloud import storage

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"
    
    storage_client = storage.Client().from_service_account_json('.credentials/keys.json')
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    generation_match_precondition = 0
    blob.upload_from_filename(source_file_name, if_generation_match=generation_match_precondition)
    print(
        f"File {source_file_name} uploaded to {destination_blob_name}."
    )

@click.group(name='saison')
def saison():
    pass

@saison.command(name="datamaker", help="Make the data from brut_. can be either vgg|seg|total")
@click.argument("goal", nargs=1)
@click.option("--vgg_only", 
              "-vgg", 
              default=True, 
              type=bool)
def datamaker(goal:str, vgg_only:bool=True):
    if goal == 'total':
        data_total()
    elif goal == 'seg':
        
        data_vgg_seg()
        if not vgg_only:
            data_seg()
    elif goal == "vgg":
        data_vgg_cls()
    else:
        print("I did not understand the command, try with total, seg or vgg.")


@saison.command(name="train_val_fol")
@click.option("--task", 
              "-t",
              default="vgg")
@click.option("--nb_img",
              "-nb", 
              default=400, 
              type=int)
def train_val_fol(task:str="vgg", nb_img:int=400):
    if task == "vgg":
        folder = "vgg_classification"
        folder_data = "datasets"
    elif task == "seg":
        folder = 'yolo_segmentation'
        folder_data = "dataset_cropped"
    
    root_dir = os.path.join('data', folder, folder_data)
    train_dir = os.path.join("data", folder, 'train')
    val_dir = os.path.join("data", folder, 'val')

    make_train_val_folder(root_dir, train_path=train_dir, val_path=val_dir, nb_img=nb_img)


@saison.command(name='finetuning', help='Define if we should make the "big" or "short" classification')
@click.argument("type_finetuning", nargs=1)
@click.option('--from_checkpoint',
              '-ckpt', 
              default=False, 
              type=bool)
@click.option('--epochs', 
              '-e', 
              default=20, 
              type=int)
@click.option('--from_epoch', 
              '-f', 
              default=0, 
              type=int)
@click.option('--images', 
              '-i', 
              default=400, 
              type=int)
def finetuning(type_finetuning:str='big',
               from_checkpoint:bool=False,
               epochs:int=20, 
               from_epoch:int=0, 
               images:int=400):

    if type_finetuning == 'small':
        folder = "yolo_segmentation"
        dataset = "dataset_cropped"
        name = "vgg_classification_small.h5"
    else:
        folder = "vgg_classification"
        dataset = "datasets"
        name = "vgg_classification_big.h5"
        
    save_path = os.path.join("src", "models", folder , name)
    chekcpoint_dir = os.path.join("src", "models", folder, "checkpoint")

    root_dir = os.path.join('data', folder, dataset)
    train_dir = os.path.join("data", folder, 'train')
    val_dir = os.path.join("data", folder, 'val')

    make_train_val_folder(root_dir, train_path=train_dir, 
                          val_path=val_dir, 
                          nb_img=images)
    train_gen, val_gen = make_generator(train_path=train_dir, val_path=val_dir)

    fit_and_export(train_gen, val_gen, save_path=save_path, 
                   checkpoint_dir=chekcpoint_dir, 
                   from_pretrained=from_checkpoint,
                   epochs=epochs, from_epoch=from_epoch)
    
@saison.command("upload", help='upload a file to bucket')
@click.option("--weights", 
              "-w",
              type=str)
@click.option("--model", 
              "-m", 
              default="all", 
              type=str)
def upload(weights:str, model:str="all"):
    base_path = os.path.join("src", "models")
    if weights == "cls":
        source = os.path.join(base_path, "vgg_classification", "big", "checkpoint"," vgg16-0031.weights.h5")
        dest = "vgg_classification.weights.h5"

    elif weights == "seg":
        base_path = os.path.join(base_path, "yolo_segmentation")
        if model == "vgg":
            source = os.path.join(base_path, "model")
            dest = "vgg_segmentation.weights.h5"
        elif model == "yolo":
            source = os.path.join(base_path, "runs", "detect_iter1", "train", "weights", "best.pt")
            dest = "yolo_segmentation.pt"

    elif weights == "total":
        source = os.path.join(base_path, "yolo_total", "runs", "detect_iter3", "train", "weights", "best.pt")
        dest = "yolo_total.pt"
    upload_blob("all-weights", 
                source_file_name=source, 
                destination_blob_name=dest)
    
    pass

@saison.command(name="load_models", help="Load models from bucket")
def load_models():
    model.load_models()
