from audio_separator.separator import Separator
import os

from pathlib import Path
class VocalMusicExtractor:
    model_name=""
    def __init__(self, model_name):
        self.model_name = model_name
    def extract_vocal_music(self,input_audio_file_path,output_audio_folder):
        # Create a separator instance
        separator = Separator(
            output_dir=f"{output_audio_folder}",        # where to save separated stems
            model_file_dir="~/models"  # optional cache for models
        )

        # Load the model (you can specify your model name / filename)
        separator.load_model(model_filename=f"{self.model_name}.onnx")

        # Separate a file
        result_paths = separator.separate(input_audio_file_path)

        for file in result_paths:
            old_file=f'{output_audio_folder}/{file}'
            new_file=file.replace(self.model_name,"").replace("(","").replace(")","")
            new_file=f'{output_audio_folder}/{new_file}'
            os.rename(old_file,new_file)

        instrumental_file=input_audio_file_path.replace(".mp3","_Instrumental_.wav")
        vocals_file=input_audio_file_path.replace(".mp3","Vocals.wav")
        return (instrumental_file,vocals_file)