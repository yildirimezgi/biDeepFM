# -*- coding:utf-8 -*-
"""
Author:
    Ezgi Yildirim, yildirimez@itu.edu.tr

Reference:
    [1] Yıldırım, Ezgi, Payam Azad, and Şule Gündüz Öğüdücü. "biDeepFM: A multi-objective deep factorization machine for reciprocal recommendation." Engineering Science and Technology, an International Journal (2021).

"""

import tensorflow as tf

from ..input_embedding import preprocess_input_embedding
from ..layers.core import PredictionLayer, DNN
from ..layers.interaction import InteractingLayer
from ..layers.utils import concat_fun
from ..utils import check_feature_config_dict


def biAutoInt(feature_dim_dict, embedding_size=8, att_layer_num=3, att_embedding_size=8, att_head_num=2, att_res=True,
            dnn_hidden_units=(256, 256), dnn_activation='relu',
            l2_reg_dnn=0, l2_reg_embedding=1e-5, dnn_use_bn=False, dnn_dropout=0, init_std=0.0001, seed=1024,
            task='binary', ):
    """Instantiates the Multi-objective AutoInt Network architecture.

    :param feature_dim_dict: dict,to indicate sparse field and dense field like {'sparse':{'field_1':4,'field_2':3,'field_3':2},'dense':['field_4','field_5']}
    :param embedding_size: positive integer,sparse feature embedding_size
    :param att_layer_num: int.The InteractingLayer number to be used.
    :param att_embedding_size: int.The embedding size in multi-head self-attention network.
    :param att_head_num: int.The head number in multi-head  self-attention network.
    :param att_res: bool.Whether or not use standard residual connections before output.
    :param dnn_hidden_units: list,list of positive integer or empty list, the layer number and units in each layer of DNN
    :param dnn_activation: Activation function to use in DNN
    :param l2_reg_dnn: float. L2 regularizer strength applied to DNN
    :param l2_reg_embedding: float. L2 regularizer strength applied to embedding vector
    :param dnn_use_bn:  bool. Whether use BatchNormalization before activation or not in DNN
    :param dnn_dropout: float in [0,1), the probability we will drop out a given DNN coordinate.
    :param init_std: float,to use as the initialize std of embedding vector
    :param seed: integer ,to use as random seed.
    :param task: str, ``"binary"`` for  binary logloss or  ``"regression"`` for regression loss
    :return: A Keras model instance.
    """

    if len(dnn_hidden_units) <= 0 and att_layer_num <= 0:
        raise ValueError("Either hidden_layer or att_layer_num must > 0")
    check_feature_config_dict(feature_dim_dict)

    deep_emb_list, _, _, inputs_list = preprocess_input_embedding(feature_dim_dict,
                                                                  embedding_size,
                                                                  l2_reg_embedding,
                                                                  0, init_std,
                                                                  seed,
                                                                  create_linear_weight=False)

    att_input = concat_fun(deep_emb_list, axis=1)

    for _ in range(att_layer_num):
        att_input = InteractingLayer(
            att_embedding_size, att_head_num, att_res)(att_input)
    att_output = tf.keras.layers.Flatten()(att_input)

    deep_input = tf.keras.layers.Flatten()(concat_fun(deep_emb_list))

    if len(dnn_hidden_units) > 0 and att_layer_num > 0:  # Deep & Interacting Layer
        deep_out = DNN(dnn_hidden_units, dnn_activation, l2_reg_dnn, dnn_dropout,
                       dnn_use_bn, seed)(deep_input)
        stack_out = tf.keras.layers.Concatenate()([att_output, deep_out])
        final_logit = tf.keras.layers.Dense(
            1, use_bias=False, activation=None)(stack_out)
        final_logit_1 = tf.keras.layers.Dense(
            1, use_bias=False, activation=None)(stack_out)
    elif len(dnn_hidden_units) > 0:  # Only Deep
        deep_out = DNN(dnn_hidden_units, dnn_activation, l2_reg_dnn, dnn_dropout,
                       dnn_use_bn, seed)(deep_input)
        final_logit = tf.keras.layers.Dense(
            1, use_bias=False, activation=None)(deep_out)
        final_logit_1 = tf.keras.layers.Dense(
            1, use_bias=False, activation=None)(deep_out)
    elif att_layer_num > 0:  # Only Interacting Layer
        final_logit = tf.keras.layers.Dense(
            1, use_bias=False, activation=None)(att_output)
        final_logit_1 = tf.keras.layers.Dense(
            1, use_bias=False, activation=None)(att_output)
    else:  # Error
        raise NotImplementedError

    output = PredictionLayer(task)(final_logit)
    output_1 = PredictionLayer(task)(final_logit_1)

    model = tf.keras.models.Model(inputs=inputs_list, outputs=[output, output_1])

    return model
