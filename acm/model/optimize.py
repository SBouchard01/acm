import joblib
import os, shutil
from pathlib import Path
from acm.model.train import TrainFCN


def objective(trial, same_n_hidden = True, **kwargs):
    """
    Train the model with the hyperparameters suggested by the optuna optimization.

    Parameters
    ----------
    trial : 
        `optuna` trial object.
    same_n_hidden : bool, optional
        If True, all the hidden layers will have the same number of neurons. If False, each hidden layer will have a different number of neurons.
        Defaults to True.
    **kwargs :
        Keyword arguments to pass to the TrainFCN function, apart from the hyperparameters.
        
    Returns
    -------
    value : float
        Validation loss of the model (from TrainFCN).
    """
    # Define the hyperparameters to optimize
    learning_rate = trial.suggest_float("learning_rate", 1.0e-3, 0.01)
    weight_decay = trial.suggest_float("weight_decay", 1.0e-5, 0.001)
    n_layers = trial.suggest_int("n_layers", 1, 10)
    if same_n_hidden:
        n_hidden = [trial.suggest_int("n_hidden", 200, 1024)] * n_layers
    else:
        n_hidden = [
            trial.suggest_int(f"n_hidden_{layer}", 200, 1024)
            for layer in range(n_layers)
        ]
    dropout_rate = trial.suggest_float("dropout_rate", 0.0, 0.15)
    
    # Train the model with the hyperparameters
    return TrainFCN(learning_rate=learning_rate,
                    n_hidden=n_hidden,
                    dropout_rate=dropout_rate,
                    weight_decay=weight_decay,
                    **kwargs)


def get_best_model(
    statistic: str,
    study_dir: str,
    checkpoint_offset: int = 0,
    copy_to: str = False,
    model_symlink: str = None,
    )-> Path: 
    """
    Get the best model checkpoint from the study.

    Parameters
    ----------
    statistic : str
        Statistic name
    study_dir : str
        Directory where the study is saved.
    checkpoint_offset : int, optional
        How many models already existed in the study directory before the training. Defaults to 0.
    copy_to : str, optional
        If given, the model will be copied to this path. Defaults to False.
        As the standard practice, the model will be copied to a '{statistic}' subdirectory in the given path.
    model_symlink : str, optional
        Name of the symlink to create when copying the model. If set to None, the symlink will be named 'last.ckpt'. Defaults to None.

    Returns
    -------
    Path
        Path to the best model checkpoint.

    Raises
    ------
    FileNotFoundError
        If the model checkpoint does not exist.
    """
    study_dir = Path(study_dir)
    
    # Open the study, and get the best trial
    study_fn = study_dir / f'{statistic}.pkl'
    study = joblib.load(study_fn)
    best_trial = study.best_trial
    
    # get the best model ckeckpoint name
    if best_trial.number == 0 and checkpoint_offset == 0:
        ckpt = 'last.ckpt'
    else:
        ckpt = f'last-v{best_trial.number + checkpoint_offset}.ckpt'
    
    model_symlnk = study_dir / statistic / ckpt
    model_fn = model_symlnk.resolve()
    
    if not model_fn.exists():
        raise FileNotFoundError(f'The model checkpoint {model_fn} does not exist.')

    # Copy to the desired path and create the symlink
    if copy_to:
        Path(copy_to).mkdir(parents=True, exist_ok=True) # Check if the directory exists, if not create it
        model_fn = shutil.copy(model_fn, copy_to) # Copy the model to the desired path
        # Create the symlink
        if model_symlink:
            symlink = Path(copy_to) / model_symlink
        else:
            symlink = Path(copy_to) / 'last.ckpt' # To follow pytorch convention
        os.symlink(model_fn, symlink)
        return model_fn
    
    return model_fn

# TODO : toy example to test the function