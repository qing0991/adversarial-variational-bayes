from numpy import save as save_array
from os.path import join as path_join
from numpy import repeat
from avb.utils.visualisation import plot_latent_2d, plot_sampled_data, plot_reconstructed_data
from avb.model_trainer import AVBModelTrainer, VAEModelTrainer
from avb.utils.datasets import load_npoints, load_mnist
from avb.utils.logger import logger

from keras.backend import clear_session
# import tensorflow as tf
# from keras.backend.tensorflow_backend import set_session
# config = tf.ConfigProto()
# config.gpu_options.per_process_gpu_memory_fraction = 0.9
# set_session(tf.Session(config=config))


def run_synthetic_experiment(model='vae', pretrained_model=None):
    logger.info("Starting an experiment on the synthetic dataset using {} model".format(model))
    data_dim = 4
    data = load_npoints(n=data_dim)

    train_data, train_labels = data['data'], data['target']

    if model == 'vae':
        trainer = VAEModelTrainer(data_dim=data_dim, latent_dim=2, experiment_name='synthetic', overwrite=True,
                                  optimiser_params={'lr': 0.001}, pretrained_dir=pretrained_model)
    elif model == 'avb':
        trainer = AVBModelTrainer(data_dim=data_dim, latent_dim=2, noise_dim=data_dim, experiment_name='synthetic',
                                  overwrite=True, use_adaptive_contrast=False,
                                  optimiser_params={'encdec': {'lr': 0.0008, 'beta_1': 0.5},
                                                    'disc': {'lr': 0.0008, 'beta_1': 0.5}},
                                  pretrained_dir=pretrained_model)
    elif model == 'avb+ac':
        trainer = AVBModelTrainer(data_dim=data_dim, latent_dim=2, noise_dim=data_dim, noise_basis_dim=8,
                                  experiment_name='synthetic',  overwrite=True, use_adaptive_contrast=True,
                                  optimiser_params={'encdec': {'lr': 0.0005, 'beta_1': 0.5},
                                                    'disc': {'lr': 0.0007, 'beta_1': 0.5}},
                                  pretrained_dir=pretrained_model)
    else:
        raise ValueError('Unknown model type. Supported models: `vae`, `avb` and `avb+ac`.')

    model_dir = trainer.run_training(train_data, batch_size=400, epochs=200)
    # model_dir = "output/"
    trained_model = trainer.get_model()

    sampling_size = 1000
    augmented_data = repeat(train_data, sampling_size, axis=0)
    augmented_labels = repeat(train_labels, sampling_size, axis=0)

    reconstructions = trained_model.reconstruct(train_data, batch_size=1000, sampling_size=sampling_size)
    save_array(path_join(model_dir, 'reconstructed_samples.npy'), reconstructions)
    plot_reconstructed_data(augmented_data[:100], reconstructions[:100], fig_dirpath=model_dir)

    latent_vars = trained_model.infer(train_data, batch_size=1000, sampling_size=sampling_size)
    save_array(path_join(model_dir, 'latent_samples.npy'), latent_vars)
    plot_latent_2d(latent_vars, augmented_labels, fig_dirpath=model_dir)

    generations = trained_model.generate(n_samples=100, batch_size=100)
    save_array(path_join(model_dir, 'generated_samples.npy'), generations)
    plot_sampled_data(generations, fig_dirpath=model_dir)

    clear_session()
    return model_dir


def run_mnist_experiment(model='vae'):
    logger.info("Starting an experiment on the MNIST dataset using {} model".format(model))
    data_dim = 28**2
    latent_dim = 8
    data = load_mnist(binarised=True, one_hot=False)
    test_data_size = 100
    train_data, train_labels = data['data'][:-test_data_size], data['target'][:-test_data_size]
    test_data, test_labels = data['data'][-test_data_size:], data['target'][-test_data_size:]

    if model == 'vae':
        trainer = VAEModelTrainer(data_dim=data_dim, latent_dim=latent_dim,
                                  experiment_name='mnist', overwrite=True,
                                  optimiser_params={'lr': 0.001})
    elif model == 'avb':
        trainer = AVBModelTrainer(data_dim=data_dim, latent_dim=latent_dim, noise_dim=16,
                                  experiment_name='mnist', overwrite=True, use_adaptive_contrast=False,
                                  optimiser_params={'encdec': {'lr': 0.001, 'beta_1': 0.5},
                                                    'disc': {'lr': 0.001, 'beta_1': 0.5}})
    elif model == 'avb+ac':
        trainer = AVBModelTrainer(data_dim=data_dim, latent_dim=latent_dim, noise_dim=16, noise_basis_dim=32,
                                  experiment_name='mnist', overwrite=True, use_adaptive_contrast=True,
                                  optimiser_params={'encdec': {'lr': 1e-4, 'beta_1': 0.5},
                                                    'disc': {'lr': 2e-4, 'beta_1': 0.5}})
    else:
        raise ValueError('Unknown model type. Supported models: `vae`, `avb` and `avb+ac`.')

    model_dir = trainer.run_training(train_data, batch_size=64, epochs=1)
    trained_model = trainer.get_model()

    sampling_size = 100
    reconstructions = trained_model.reconstruct(test_data,
                                                batch_size=min(1000, test_data_size),
                                                sampling_size=sampling_size)
    save_array(path_join(model_dir, 'reconstructed_samples.npy'), reconstructions)
    plot_reconstructed_data(test_data, reconstructions[::sampling_size], fig_dirpath=model_dir)

    latent_vars = trained_model.infer(test_data,
                                      batch_size=min(1000, test_data_size),
                                      sampling_size=sampling_size)
    save_array(path_join(model_dir, 'latent_samples.npy'), latent_vars)
    if latent_dim == 2:
        repeated_labels = repeat(test_labels, sampling_size, axis=0)
        plot_latent_2d(latent_vars, repeated_labels, fig_dirpath=model_dir)

    generations = trained_model.generate(n_samples=100, batch_size=100)
    save_array(path_join(model_dir, 'generated_samples.npy'), generations)
    plot_sampled_data(generations, fig_dirpath=model_dir)
    return model_dir


if __name__ == '__main__':
    run_synthetic_experiment('avb+ac', pretrained_model='output/avb_with_ac/synthetic/final')
