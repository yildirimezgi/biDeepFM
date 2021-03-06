# -*- coding:utf-8 -*-
"""
Author:
    Ezgi Yildirim, yildirimez@itu.edu.tr

Reference:
    [1] Yıldırım, Ezgi, Payam Azad, and Şule Gündüz Öğüdücü. "biDeepFM: A multi-objective deep factorization machine for reciprocal recommendation." Engineering Science and Technology, an International Journal (2021).

"""

import tensorflow as tf

from ..input_embedding import preprocess_input_embedding, get_linear_logit
from ..layers.core import PredictionLayer, DNN
from ..layers.interaction import BiInteractionPooling
from ..layers.utils import concat_fun
from ..utils import check_feature_config_dict


def biNFM(feature_dim_dict, embedding_size=8,
        dnn_hidden_units=(128, 128), l2_reg_embedding=1e-5, l2_reg_linear=1e-5, l2_reg_dnn=0,
        init_std=0.0001, seed=1024, bi_dropout=0, dnn_dropout=0, dnn_activation='relu', task='binary',
        ):
    """Instantiates the Multi-objective Neural Factorization Machine architecture.

    :param feature_dim_dict: dict,to indicate sparse field and dense field like {'sparse':{'field_1':4,'field_2':3,'field_3':2},'dense':['field_4','field_5']}
    :param embedding_size: positive integer,sparse feature embedding_size
    :param dnn_hidden_units: list,list of positive integer or empty list, the layer number and units in each layer of deep net
    :param l2_reg_embedding: float. L2 regularizer strength applied to embedding vector
    :param l2_reg_linear: float. L2 regularizer strength applied to linear part.
    :param l2_reg_dnn: float . L2 regularizer strength applied to DNN
    :param init_std: float,to use as the initialize std of embedding vector
    :param seed: integer ,to use as random seed.
    :param biout_dropout: When not ``None``, the probability we will drop out the output of BiInteractionPooling Layer.
    :param dnn_dropout: float in [0,1), the probability we will drop out a given DNN coordinate.
    :param dnn_activation: Activation function to use in deep net
    :param task: str, ``"binary"`` for  binary logloss or  ``"regression"`` for regression loss
    :return: A Keras model instance.
    """
    check_feature_config_dict(feature_dim_dict)

    deep_emb_list, linear_emb_list, dense_input_dict, inputs_list = preprocess_input_embedding(feature_dim_dict,
                                                                                               embedding_size,
                                                                                               l2_reg_embedding,
                                                                                               l2_reg_linear, init_std,
                                                                                               seed,
                                                                                               create_linear_weight=True)

    linear_logit = get_linear_logit(linear_emb_list, dense_input_dict, l2_reg_linear)
    linear_logit_1 = get_linear_logit(linear_emb_list, dense_input_dict, l2_reg_linear)

    fm_input = concat_fun(deep_emb_list, axis=1)
    bi_out = BiInteractionPooling()(fm_input)
    if bi_dropout:
        bi_out = tf.keras.layers.Dropout(bi_dropout)(bi_out, training=None)
    deep_out = DNN(dnn_hidden_units, dnn_activation, l2_reg_dnn, dnn_dropout,
                   False, seed)(bi_out)
    deep_logit = tf.keras.layers.Dense(
        1, use_bias=False, activation=None)(deep_out)
    deep_logit_1 = tf.keras.layers.Dense(
        1, use_bias=False, activation=None)(deep_out)

    final_logit = linear_logit
    final_logit_1 = linear_logit_1

    if len(dnn_hidden_units) > 0:
        final_logit = tf.keras.layers.add([final_logit, deep_logit])
        final_logit_1 = tf.keras.layers.add([final_logit_1, deep_logit_1])

    output = PredictionLayer(task)(final_logit)
    output_1 = PredictionLayer(task)(final_logit_1)

    model = tf.keras.models.Model(inputs=inputs_list, outputs=[output, output_1])
    return model
