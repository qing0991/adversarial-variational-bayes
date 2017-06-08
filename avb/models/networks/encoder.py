import logging
import keras.backend as ker

from keras.models import Input
from keras.layers import Lambda
from keras.models import Model

from architectures import get_network_by_name

logger = logging.getLogger(__name__)


class Encoder(object):
    """
    An Encoder model is trained to parametrise an arbitrary posterior approximate distribution given some 
    input x, i.e. q(z|x). The model takes as input concatenated data samples and arbitrary noise and produces
    a latent encoding:
    
      Data     Noise
       |         |
       ----------- <-- concatenation
            | 
       -----------
       | Encoder |
       -----------
            |
        Latent space
    
    """
    def __init__(self, data_dim, noise_dim, latent_dim, network_architecture='synthetic'):
        """
        Args:
            data_dim: int, flattened data space dimensionality 
            noise_dim: int, flattened noise space dimensionality
            latent_dim: int, flattened latent space dimensionality
            network_architecture: str, the architecture name for the body of the Encoder model
        """
        logger.info("Initialising Encoder model with {} dimensional data and {} dimensional noise input "
                    "and {} dimensional latent output".format(data_dim, noise_dim, latent_dim))

        data_input = Input(shape=(data_dim,), name='enc_input_data')
        noise_input = Input(shape=(noise_dim,), name='enc_input_noise')

        latent_factors = get_network_by_name['encoder'][network_architecture]([data_input, noise_input], latent_dim)

        self.encoder_model = Model(inputs=[data_input, noise_input], outputs=latent_factors, name='encoder')

    def __call__(self, *args, **kwargs):
        """
        Make the Encoder model callable on a list of Input layers.
        
        Args:
            *args: a list of input layers from the super-model or numpy arrays in case of test-time inference.
            **kwargs: 

        Returns:
            An Encoder model.
        """
        return self.encoder_model(args[0])


class MomentEstimationEncoder(object):
    """
    An Encoder model is trained to parametrise an arbitrary posterior approximate distribution given some 
    input x, i.e. q(z|x). The model takes as input concatenated data samples and arbitrary noise and produces
    a latent encoding. Additionally the first two moments (mean and variance) are estimated empirically, which is
    necessary for the Adaptive Contrast learning algorithm. Schematically it can be represented as follows:

       Data  Noise
        |      |
        |      |
        |      | 
       -----------
       | Encoder |  ----> empirical mean and variance
       -----------
            |
        Latent space

    """

    def __init__(self, data_dim, noise_dim, latent_dim, network_architecture='mnist'):
        """
        Args:
            data_dim: int, flattened data space dimensionality 
            noise_dim: int, flattened noise space dimensionality
            latent_dim: int, flattened latent space dimensionality
            network_architecture: str, the architecture name for the body of the moment estimation Encoder model
        """
        logger.info("Initialising moment estimation Encoder model with {} dimensional data and {} dimensional "
                    "noise input and {} dimensional latent output".format(data_dim, noise_dim, latent_dim))

        data_input = Input(shape=(data_dim,), name='enc_input_data')
        noise_input = Input(shape=(noise_dim,), name='enc_input_noise')
        sampling_input = Input(shape=(noise_dim,), name='enc_input_moment_estimator_sampling')

        latent_factors, mean, var = get_network_by_name['moment_estimation_encoder'][network_architecture](
            [data_input, noise_input, sampling_input], latent_dim)

        self.encoder_model = Model(inputs=[data_input, noise_input], outputs=latent_factors, name='encoder')
        self.moment_estimation_model = Model(inputs=[data_input, sampling_input], outputs=[mean, var],
                                             name='encoder_moment_estimation')

    def __call__(self, *args, **kwargs):
        """
        Make the Encoder model callable on a list of Input layers.

        Args:
            *args: a list of input layers from the super-model or numpy arrays in case of test-time inference.
            **kwargs: 

        Returns:
            An Encoder model.
        """
        estimate_moments = kwargs.get('estimate_moments', False)
        if estimate_moments:
            return self.moment_estimation_model(args[0])
        else:
            return self.encoder_model(args[0])


class ReparametrisedGaussianEncoder(object):
    """
    A ReparametrisedGaussianEncoder model is trained to parametrise a Gaussian latent variables:

           Data              
            | 
       -----------
       | Encoder |
       -----------
            |
    mu + sigma * Noise   <--- Reparametrised Gaussian latent space

    """

    def __init__(self, data_dim, noise_dim, latent_dim, network_architecture='synthetic'):
        """
        Args:
            data_dim: int, flattened data space dimensionality 
            noise_dim: int, flattened noise space dimensionality
            latent_dim: int, flattened latent space dimensionality
            network_architecture: str, the architecture name for the body of the reparametrised Gaussian Encoder model
        """
        logger.info("Initialising Reparametrised Gaussian Encoder model with {} dimensional data "
                    "and {} dimensional latent output".format(data_dim, noise_dim, latent_dim))

        data_input = Input(shape=(data_dim,), name='rep_enc_input_data')
        noise_input = Input(shape=(noise_dim,), name='rep_enc_input_noise')

        latent_mean, latent_log_var = get_network_by_name['reparametrised_encoder'][network_architecture](data_input,
                                                                                                          latent_dim)

        latent_factors = Lambda(lambda x: x[0] + ker.exp(x[1] / 2.0) * x[2],
                                name='rep_enc_reparametrised_latent')([latent_mean, latent_log_var, noise_input])

        self.encoder_inference_model = Model(inputs=[data_input, noise_input], outputs=latent_factors,
                                             name='reparametrised_encoder')
        self.encoder_learning_model = Model(inputs=[data_input, noise_input],
                                            outputs=[latent_factors, latent_mean, latent_log_var])

    def __call__(self, *args, **kwargs):
        """
        Make the Encoder model callable on a list of Input layers.

        Args:
            *args: a list of input layers from the super-model or numpy arrays in case of test-time inference.

        Keyword Args:
            is_learning: bool, whether the model is used for training or inference. The output is either 
                the latent space or the latent space and the means and variances from which it is reparametrised.  

        Returns:
            An Encoder model.
        """
        is_learninig = kwargs.get('is_learning', True)
        if is_learninig:
            return self.encoder_learning_model(args[0])
        else:
            return self.encoder_inference_model(args[0])
