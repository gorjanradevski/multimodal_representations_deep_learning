import tensorflow as tf
from tensorflow.contrib import layers
from tensorflow.contrib.framework.python.ops import arg_scope
from tensorflow.contrib.layers.python.layers import layers as layers_lib
from tensorflow.python.ops import variable_scope

from training.cells import cell_factory
from training.optimizers import optimizer_factory


class Text2ImageMatchingModel:
    def __init__(
        self,
        seed: int,
        images: tf.Tensor,
        captions: tf.Tensor,
        captions_len: tf.Tensor,
        rnn_hidden_size: int,
        vocab_size: int,
        embedding_size: int,
        cell_type: str,
        num_layers: int,
        attn_size1: int,
        attn_size2: int,
        optimizer_type: str,
        learning_rate: float,
        clip_value: int,
    ):
        # Define global saver
        self.saver = tf.train.Saver(defer_build=True)
        self.keep_prob = tf.placeholder_with_default(1.0, None, name="keep_prob")
        self.weight_decay = tf.placeholder_with_default(0.0, None, name="weight_decay")
        self.image_encoded = self.image_encoder_graph(images, rnn_hidden_size)
        self.text_encoded = self.text_encoder_graph(
            seed,
            captions,
            captions_len,
            vocab_size,
            embedding_size,
            cell_type,
            rnn_hidden_size,
            num_layers,
            self.keep_prob,
        )
        self.attended_image = self.join_attention_graph(
            seed, attn_size1, attn_size2, self.image_encoded, reuse=False
        )
        self.attended_text = self.join_attention_graph(
            seed, attn_size1, attn_size2, self.text_encoded, reuse=True
        )
        """
        Commented out for now so that the tests pass (After loss is included it will
        be uncommented).
        self.loss = self.compute_loss(
            self.attended_image, self.attended_text, self.weight_decay
        )
        self.optimize = self.apply_gradients_op(
            self.loss, optimizer_type, learning_rate, clip_value
        )
        """
        self.image_encoder_loader = self.create_image_encoder_loader()
        self.saver.build()

    @staticmethod
    def image_encoder_graph(images: tf.Tensor, rnn_hidden_size: int) -> tf.Tensor:
        """Extract higher level features from the image using a conv net pretrained on
        Image net.

        As per: https://github.com/tensorflow/tensorflow/blob/master/tensorflow/contrib/
        slim/python/slim/nets/vgg.py

        Args:
            images: The input images.
            rnn_hidden_size: The hidden size of its text counterpart.

        Returns:
            The encoded image.

        """
        with variable_scope.variable_scope(
            "image_encoder", "image_encoder", [images]
        ) as sc:
            end_points_collection = sc.original_name_scope + "_end_points"
            with arg_scope(
                [layers.conv2d, layers_lib.fully_connected, layers_lib.max_pool2d],
                outputs_collections=end_points_collection,
            ):
                net = layers_lib.repeat(
                    images, 2, layers.conv2d, 64, [3, 3], scope="conv1", trainable=False
                )
                net = layers_lib.max_pool2d(net, [2, 2], scope="pool1")
                net = layers_lib.repeat(
                    net, 2, layers.conv2d, 128, [3, 3], scope="conv2", trainable=False
                )
                net = layers_lib.max_pool2d(net, [2, 2], scope="pool2")
                net = layers_lib.repeat(
                    net, 3, layers.conv2d, 256, [3, 3], scope="conv3", trainable=False
                )
                net = layers_lib.max_pool2d(net, [2, 2], scope="pool3")
                net = layers_lib.repeat(
                    net, 3, layers.conv2d, 512, [3, 3], scope="conv4", trainable=False
                )
                net = layers_lib.max_pool2d(net, [2, 2], scope="pool4")
                net = layers_lib.repeat(
                    net, 3, layers.conv2d, 512, [3, 3], scope="conv5", trainable=False
                )
                image_feature_extractor = layers_lib.max_pool2d(
                    net, [2, 2], scope="pool5"
                )
                project_layer = tf.layers.dense(
                    image_feature_extractor, 2 * rnn_hidden_size, name="project_image"
                )
                return tf.cast(
                    tf.reshape(
                        project_layer,
                        [
                            -1,
                            project_layer.shape[1] * project_layer.shape[2],
                            2 * rnn_hidden_size,
                        ],
                    ),
                    tf.float32,
                )

    @staticmethod
    def text_encoder_graph(
        seed: int,
        captions: tf.Tensor,
        captions_len: tf.Tensor,
        vocab_size: int,
        embedding_size: int,
        cell_type: str,
        rnn_hidden_size: int,
        num_layers: int,
        keep_prob: float,
    ):
        """Encodes the text it gets as input using a bidirectional rnn.

        Args:
            seed: The random seed.
            captions: The inputs.
            captions_len: The length of the inputs.
            vocab_size: The size of the vocabulary.
            embedding_size: The size of the embedding layer.
            cell_type: The cell type.
            rnn_hidden_size: The size of the weight matrix in the cell.
            num_layers: The number of layers of the rnn.
            keep_prob: The dropout probability (1.0 means keep everything)

        Returns:
            The encoded the text.

        """
        with tf.variable_scope("text_encoder"):
            embeddings = tf.Variable(
                tf.random_uniform([vocab_size, embedding_size], -1.0, 1.0),
                dtype=tf.float32,
                trainable=True,
            )
            inputs = tf.nn.embedding_lookup(embeddings, captions)
            cell_fw = cell_factory(
                seed, cell_type, rnn_hidden_size, num_layers, keep_prob
            )
            cell_bw = cell_factory(
                seed, cell_type, rnn_hidden_size, num_layers, keep_prob
            )
            (output_fw, output_bw), _ = tf.nn.bidirectional_dynamic_rnn(
                cell_fw, cell_bw, inputs, sequence_length=captions_len, dtype=tf.float32
            )
        return tf.concat([output_fw, output_bw], axis=2)

    @staticmethod
    def join_attention_graph(
        seed: int,
        attn_size1: int,
        attn_size2: int,
        encoded_input: tf.Tensor,
        reuse=False,
    ):
        """Applies the same attention on the encoded image and the encoded text.

        As per: https://arxiv.org/pdf/1703.03130.pdf

        The "A structured self-attentative sentence embedding" paper goes through
        the attention mechanism applied here.

        Args:
            seed: The random seed to initialize the weights.
            attn_size1: The size of the first projection.
            attn_size2: The size of the second projection.
            encoded_input: The encoded input, can be both the image and the text.
            reuse: Whether to reuse the variables during the second creation.

        Returns:
            Attended output.

        """
        with tf.variable_scope("joint_attention"):
            project = tf.layers.dense(
                encoded_input,
                attn_size1,
                activation=tf.nn.tanh,
                kernel_initializer=tf.glorot_uniform_initializer(seed=seed),
                bias_initializer=tf.zeros_initializer(),
                reuse=reuse,
                name="Wa1",
            )
            alphas = tf.layers.dense(
                project,
                attn_size2,
                activation=tf.nn.softmax,
                kernel_initializer=tf.glorot_uniform_initializer(seed=seed),
                bias_initializer=tf.zeros_initializer(),
                reuse=reuse,
                name="Wa2",
            )
        return tf.matmul(tf.transpose(encoded_input, [0, 2, 1]), alphas)

    @staticmethod
    def compute_loss(
        attended_image: tf.Tensor, attended_text: tf.Tensor, weight_decay: float
    ) -> tf.Tensor:
        pass

    @staticmethod
    def apply_gradients_op(
        loss: tf.Tensor, optimizer_type: str, learning_rate: float, clip_value: int
    ) -> tf.Operation:
        """Applies the gradients on the variables.

        Args:
            loss: The computed loss.
            optimizer_type: The type of the optmizer.
            learning_rate: The optimizer learning rate.
            clip_value: The clipping value.

        Returns:
            An operation node to be executed in order to apply the computed gradients.

        """
        optimizer = optimizer_factory(optimizer_type, learning_rate)
        gradients, variables = zip(*optimizer.compute_gradients(loss))
        gradients, _ = tf.clip_by_global_norm(gradients, clip_value)

        return optimizer.apply_gradients(zip(gradients, variables))

    @staticmethod
    def create_image_encoder_loader():
        """Creates a loader that can be used to load the image encoder.

        Returns:
            A use-case specific loader.

        """
        variables_to_restore = tf.contrib.framework.get_variables_to_restore(
            exclude=["image_encoder/project_image/", "text_encoder/", "join_attention/"]
        )
        return tf.train.Saver(variables_to_restore)

    @staticmethod
    def init(sess: tf.Session) -> None:
        """Initializes all variables in the graph.

        Args:
            sess: The active session.

        Returns:
            None

        """
        sess.run(tf.global_variables_initializer())