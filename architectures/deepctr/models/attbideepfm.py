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
from ..layers.interaction import AFMLayer, FM
from ..layers.utils import concat_fun
from ..utils import check_feature_config_dict


def AttbiDeepFM(feature_dim_dict, embedding_size=8,
             use_fm=True, dnn_hidden_units=(128, 128), l2_reg_linear=0.00001, l2_reg_embedding=0.00001, l2_reg_dnn=0,
             init_std=0.0001, seed=1024, dnn_dropout=0, dnn_activation='relu', dnn_use_bn=False, task='binary'):
    """Instantiates the Attentional biDeepFM Network architecture.

    :param feature_dim_dict: dict,to indicate sparse field and dense field like {'sparse':{'field_1':4,'field_2':3,'field_3':2},'dense':['field_4','field_5']}
    :param embedding_size: positive integer,sparse feature embedding_size
    :param use_fm: bool,use FM part or not
    :param dnn_hidden_units: list,list of positive integer or empty list, the layer number and units in each layer of DNN
    :param l2_reg_linear: float. L2 regularizer strength applied to linear part
    :param l2_reg_embedding: float. L2 regularizer strength applied to embedding vector
    :param l2_reg_dnn: float. L2 regularizer strength applied to DNN
    :param init_std: float,to use as the initialize std of embedding vector
    :param seed: integer ,to use as random seed.
    :param dnn_dropout: float in [0,1), the probability we will drop out a given DNN coordinate.
    :param dnn_activation: Activation function to use in DNN
    :param dnn_use_bn: bool. Whether use BatchNormalization before activation or not in DNN
    :param task: str, ``"binary"`` for  binary logloss or  ``"regression"`` for regression loss
    :return: A Keras model instance.
    """
    use_attention = True
    attention_factor = 8
    l2_reg_att = 1e-5
    afm_dropout = 0

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
    deep_input = tf.keras.layers.Flatten()(fm_input)
    if use_attention:
        fm_out = AFMLayer(attention_factor, l2_reg_att, afm_dropout, seed)(deep_emb_list,)
        fm_out_1 = AFMLayer(attention_factor, l2_reg_att, afm_dropout, seed)(deep_emb_list, )
    else:
        fm_out = FM()(fm_input)
        fm_out_1 = FM()(fm_input)
    deep_out = DNN(dnn_hidden_units, dnn_activation, l2_reg_dnn, dnn_dropout,
                   dnn_use_bn, seed)(deep_input)
    deep_logit = tf.keras.layers.Dense(
        1, use_bias=False, activation=None)(deep_out)
    deep_logit_1 = tf.keras.layers.Dense(
        1, use_bias=False, activation=None)(deep_out)

    if len(dnn_hidden_units) == 0 and use_fm == False:  # only linear
        final_logit = linear_logit
        final_logit_1 = linear_logit_1
    elif len(dnn_hidden_units) == 0 and use_fm == True:  # linear + FM
        final_logit = tf.keras.layers.add([linear_logit, fm_out])
        final_logit_1 = tf.keras.layers.add([linear_logit_1, fm_out_1])
    elif len(dnn_hidden_units) > 0 and use_fm == False:  # linear +　Deep
        final_logit = tf.keras.layers.add([linear_logit, deep_logit])
        final_logit_1 = tf.keras.layers.add([linear_logit_1, deep_logit_1])
    elif len(dnn_hidden_units) > 0 and use_fm == True:  # linear + FM + Deep
        final_logit = tf.keras.layers.add([linear_logit, fm_out, deep_logit])
        final_logit_1 = tf.keras.layers.add([linear_logit_1, fm_out_1, deep_logit_1])
    else:
        raise NotImplementedError

    output = PredictionLayer(task)(final_logit)
    output_1 = PredictionLayer(task)(final_logit_1)
    model = tf.keras.models.Model(inputs=inputs_list, outputs=[output, output_1])
    return model

