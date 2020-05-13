# Copyright 2015 gRPC authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The Python implementation of the GRPC RemoteAttestation server."""

from concurrent import futures
import logging

import grpc

#  import rpc.remote_pb2
#  import rpc.remote_pb2_grpc
from .rpc import remote_pb2
from .rpc import remote_pb2_grpc
from rpc_utils import *
import os
import sys
import traceback
from .core import RemoteAPI as remote_api
from .rabit import RemoteAPI as rabit_remote_api

# c_bst_ulong corresponds to bst_ulong defined in xgboost/c_api.h
c_bst_ulong = ctypes.c_uint64

import threading
import types

class Command(object):
    """
    Commands submitted for execution to remote server
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self._func = None
        self._params = None
        self._ret = None
        self._usernames = []
        self._retrieved = []

    def submit(self, func, params, username):
        if self._func is None:
            self._func = func
            self._params = params
        else:
            assert self._func == func
        self._usernames.append(username)

    def is_ready(self):
        for user in globals()["all_users"]:
            if user not in self._usernames:
                return False
        return True

    def invoke(self):
        node_ips = globals().get("nodes")
        if not node_ips:
            self._ret = self._func(self._params)
        else: # We're the RPC orchestrator
            channels = []
            for channel_addr in node_ips:
                channels.append(grpc.insecure_channel(channel_addr))
        
            # Store futures in a list
            # Futures hold the result of asynchronous calls to each gRPC server
            futures = []
        
            for channel in channels:
                stub = remote_pb2_grpc.RemoteStub(channel)
        
                # Asynchronous calls to start job on each node
                if self._func == rabit_remote_api.RabitInit:
                    response_future = stub.rpc_RabitInit.future(remote_pb2.RabitParams(status=0))
                elif self._func == rabit_remote_api.RabitFinalize:
                    response_future = stub.rpc_RabitFinalize(remote_pb2.RabitParams(status=0))
                elif self._func == remote_api.XGDMatrixCreateFromEncryptedFile:
                    filenames = self._params.filenames
                    usernames = self._params.usernames
                    silent = self._params.silent
                    response_future = stub.rpc_XGDMatrixCreateFromEncryptedFile.future(remote_pb2.DMatrixAttrs(
                        filenames=filenames,
                        usernames=usernames,
                        silent=silent
                        ))
                elif self._func == remote_api.XGBoosterSetParam:
                    booster_handle = self._params.booster_handle
                    key = self._params.key
                    value = self._params.value
                    response_future = stub.rpc_XGBoosterSetParam.future(remote_pb2.BoosterParam(
                        booster_handle=booster_handle,
                        key=key,
                        value=value
                        ))
                elif self._func == remote_api.XGBoosterCreate:
                    cache = self._params.cache
                    length = self._params.length
                    response_future = stub.rpc_XGBoosterCreate.future(remote_pb2.BoosterAttrs(
                        cache=cache,
                        length=length
                        ))
                elif self._func == remote_api.XGBoosterUpdateOneIter:
                    booster_handle = self._params.booster_handle
                    dtrain_handle = self._params.dtrain_handle
                    iteration = self._params.iteration
                    response_future = stub.rpc_XGBoosterUpdateOneIter.future(remote_pb2.BoosterUpdateParams(
                        booster_handle=booster_handle,
                        dtrain_handle=dtrain_handle,
                        iteration=iteration
                        ))
                elif self._func == remote_api.XGBoosterSaveModel:
                    booster_handle = self._params.booster_handle
                    filename = self._params.filename
                    username = self._params.username
                    response_future = stub.rpc_XGBoosterSaveModel.future(remote_pb2.SaveModelParams(
                        booster_handle=booster_handle,
                        filename=filename,
                        username=username
                        ))
                elif self._func == remote_api.XGBoosterLoadModel:
                    booster_handle = self._params.booster_handle
                    filename = self._params.filename
                    username = username
                    response_future = stub.rpc_XGBoosterLoadModel.future(remote_pb2.LoadModelParams(
                        booster_handle=booster_handle,
                        filename=filename,
                        username=username
                        ))
                elif self._func == remote_api.XGBoosterDumpModelEx:
                    booster_handle = self._params.booster_handle
                    fmap = self._params.fmap
                    with_stats = self._params.with_stats
                    dump_format = self._params.dump_format
                    response_future = stub.rpc_XGBoosterDumpModelEx.future(remote_pb2.DumpModelParams(
                        booster_handle=booster_handle,
                        fmap=fmap,
                        with_stats=with_stats,
                        dump_format=dump_format
                        ))
                elif self._func == remote_api.XGBoosterDumpModelExWithFeatures:
                    booster_handle = self._params.booster_handle
                    flen = self._params.flen
                    fname = self._params.fname
                    ftype = self._params.ftype
                    with_stats = self._params.with_stats
                    dump_format = self._params.dump_format
                    response_future = stub.rpc_XGBoosterDumpModelExWithFeatures.future(remote_pb2.DumpModelWithFeaturesParams(
                        booster_handle=booster_handle,
                        flen=flen,
                        fname=fname,
                        ftype=ftype,
                        with_stats=with_stats,
                        dump_format=dump_format
                        ))
                elif self._func == remote_api.XGBoosterGetModelRaw:
                    booster_handle = self._params.booster_handle
                    username = self._params.username
                    response_future = stub.rpc_XGBoosterGetModelRaw.future(remote_pb2.ModelRawParams(
                        booster_handle=booster_handle,
                        username=username
                        ))
                elif self._func == remote_api.XGDMatrixNumRow:
                    name = self._params.name
                    response_future = stub.rpc_XGDMatrixNumRow.future(remote_pb2.Name(
                        name=name
                        ))
                elif self._func == remote_api.XGDMatrixNumCol:
                    name = self._params.name
                    response_future = stub.rpc_XGDMatrixNumCol.future(remote_pb2.Name(
                        name=name
                        ))
                elif self._func == remote_api.XGBoosterPredict:
                    booster_handle = self._params.booster_handle
                    dmatrix_handle = self._params.dmatrix_handle
                    option_mask = self._params.option_mask
                    ntree_limit = self._params.ntree_limit
                    username = self._params.username
                    response_future = stub.rpc_XGBoosterPredict.future(remote_pb2.PredictParams(
                        booster_handle=booster_handle,
                        dmatrix_handle=dmatrix_handle,
                        option_mask=option_mask,
                        ntree_limit=ntree_limit,
                        username=username
                        ))
                futures.append(response_future)
        
            results = []
            for future in futures:
                results.append(future.result())

            # Set return value
            if self._func == rabit_remote_api.RabitInit:
                return_codes = [result.status for result in results]
                if sum(return_codes) == 0:
                    self._ret = 0
                else:
                    self._ret = -1
            elif self._func == rabit_remote_api.RabitFinalize:
                return_codes = [result.status for result in results]
                if sum(return_codes) == 0:
                    self._ret = 0
                else:
                    self._ret = -1
            elif self._func == remote_api.XGDMatrixCreateFromEncryptedFile:
                dmatrix_handles = [result.name for result in results]
                if dmatrix_handles.count(dmatrix_handles[0]) == len(dmatrix_handles):
                    # Every enclave returned the same handle string
                    self._ret = dmatrix_handles[0]
                else:
                    self._ret = None
            elif self._func == remote_api.XGBoosterSetParam:
                return_codes = [result.status for result in results]
                if sum(return_codes) == 0:
                    self._ret = 0
                else:
                    self._ret = -1
            elif self._func == remote_api.XGBoosterCreate:
                bst_handles = [result.name for result in results]
                if bst_handles.count(bst_handles[0]) == len(bst_handles):
                    # Every enclave returned the same booster handle string
                    self._ret = bst_handles[0]
                else:
                    self._ret = None
            elif self._func == remote_api.XGBoosterUpdateOneIter:
                return_codes = [result.status for result in results]
                if sum(return_codes) == 0:
                    self._ret = 0
                else:
                    self._ret = -1
            elif self._func == remote_api.XGBoosterSaveModel:
                return_codes = [result.status for result in results]
                if sum(return_codes) == 0:
                    self._ret = 0
                else:
                    self._ret = -1
            elif self._func == remote_api.XGBoosterLoadModel:
                return_codes = [result.status for result in results]
                if sum(return_codes) == 0:
                    self._ret = 0
                else:
                    self._ret = -1
            elif self._func == remote_api.XGBoosterDumpModelEx:
                sarrs = [result.sarr for result in results]
                lengths = [result.length for result in results]
                if lengths.count(lengths[0]) == len(lengths):
                    # Every enclave returned the same length
                    # We cannot check if the dumps are the same because they are encrypted
                    self._ret = (lengths[0], sarrs[0])
                else:
                    self._ret = (None, None)
            elif self._func == remote_api.XGBoosterDumpModelExWithFeatures:
                sarrs = [result.sarr for result in results]
                lengths = [result.length for result in results]
                if lengths.count(lengths[0]) == len(lengths):
                    # Every enclave returned the same length
                    # We cannot check if the dumps are the same because they are encrypted
                    self._ret = (lengths[0], sarrs[0])
                else:
                    self._ret = (None, None)
            elif self._func == remote_api.XGBoosterGetModelRaw:
                sarrs = [result.sarr for result in results]
                lengths = [result.length for result in results]
                if lengths.count(lengths[0]) == len(lengths):
                    # Every enclave returned the same length
                    # We cannot check if the dumps are the same because they are encrypted
                    self._ret = (lengths[0], sarrs[0])
                else:
                    self._ret = (None, None)
            elif self._func == remote_api.XGDMatrixNumRow:
                num_rows = [result.value for result in results]
                if num_rows.count(num_rows[0]) == len(num_rows):
                    # Each enclave agrees on the number of rows in the DMatrix
                    self._ret = num_rows[0]
                else:
                    self._ret = None 
            elif self._func == remote_api.XGDMatrixNumCol:
                num_cols = [result.value for result in results]
                if num_cols.count(num_cols[0]) == len(num_cols):
                    # Each enclave agrees on the number of columns in the DMatrix
                    self._ret = num_cols[0]
                else:
                    self._ret = None 
            elif self._func == remote_api.XGBoosterPredict:
                enc_preds_list = [result.predictions for result in results]
                num_preds_list = [result.num_preds for result in results] 
                if len(enc_preds_list) == len(num_preds_list):
                    self._ret = (enc_preds_list, num_preds_list)
                else:
                    self._ret = (None, None)


    def result(self, username):
        self._retrieved.append(username)
        ret = self._ret
        if self.is_complete():
            self.reset()
        return ret

    def is_complete(self):
        for user in globals()["all_users"]:
            if user not in self._retrieved:
                return False
        return True


class RemoteServicer(remote_pb2_grpc.RemoteServicer):

    def __init__(self, enclave, condition, command):
        self.enclave = enclave
        self.condition = condition
        self.command = command

    def _synchronize(self, func, params):
        username = params.username

        self.condition.acquire() 
        self.command.submit(func, params, username)
        if self.command.is_ready():
            self.command.invoke()
            ret = self.command.result(username)
            self.condition.notifyAll()
        else:
            self.condition.wait()
            ret = self.command.result(username)
        self.condition.release()
        return ret

    def rpc_get_remote_report_with_pubkey(self, request, context):
        """
        Calls get_remote_report_with_pubkey()
        """
        if not globals()["is_orchestrator"]:    
            # Get report from enclave
            pem_key, key_size, remote_report, remote_report_size = remote_api.get_remote_report_with_pubkey(request)
        else:
            node_ips = globals()["nodes"]
            master_enclave_ip = node_ips[0]
            with grpc.insecure_channel(master_enclave_ip) as channel:
                stub = remote_pb2_grpc.RemoteStub(channel)
                response = stub.rpc_get_remote_report_with_pubkey(remote_pb2.Status(status=1))

            pem_key = response.pem_key
            key_size = response.key_size
            remote_report = response.remote_report
            remote_report_size = response.remote_report_size


        return remote_pb2.Report(pem_key=pem_key, key_size=key_size, remote_report=remote_report, remote_report_size=remote_report_size)

    # FIXME implement the library call within class RemoteAPI
    # FIXME add support for this function for cluster
    def rpc_add_client_key(self, request, context):
        """
        Sends encrypted symmetric key, signature over key, and filename of data that was encrypted using the symmetric key
        """
        # Get encrypted symmetric key, signature, and filename from request
        enc_sym_key = request.enc_sym_key
        key_size = request.key_size
        signature = request.signature
        sig_len = request.sig_len

        # Get a reference to the existing enclave
        result = self.enclave._add_client_key(enc_sym_key, key_size, signature, sig_len)

        return remote_pb2.Status(status=result)

    # FIXME implement the library call within class RemoteAPI
    def rpc_add_client_key_with_certificate(self, request, context):
        """
        Calls add_client_key_with_certificate()
        """
        certificate = request.certificate
        enc_sym_key = request.enc_sym_key
        key_size = request.key_size
        signature = request.signature
        sig_len = request.sig_len
        # Get encrypted symmetric key, signature, and certificate from request
        if not globals()["is_orchestrator"]:
            # Get a reference to the existing enclave
            result = self.enclave._add_client_key_with_certificate(certificate, enc_sym_key, key_size, signature, sig_len)
            return remote_pb2.Status(status=result)
        else:
            node_ips = globals()["nodes"]
            #  master_enclave_ip = node_ips[0]
            channels = []
            for channel_addr in node_ips:
                channels.append(grpc.insecure_channel(channel_addr))

            futures = []
            for channel in channels:
                stub = remote_pb2_grpc.RemoteStub(channel)
                # The transmitted data is encrypted with the public key of rank 0 enclave
                response_future = stub.rpc_add_client_key_with_certificate.future(remote_pb2.DataMetadata(
                    certificate=certificate,
                    enc_sym_key=enc_sym_key,
                    key_size=key_size,
                    signature=signature,
                    sig_len=sig_len))

                futures.append(response_future)

            results = []
            for future in futures:
                results.append(future.result())

            return_codes = [result.status for result in results]
            if sum(return_codes) == 0:
                return remote_pb2.Status(status=0)
            else:
                return remote_pb2.Status(status=-1)


    def rpc_XGDMatrixCreateFromEncryptedFile(self, request, context):
        """
        Create DMatrix from encrypted file
        """
        try:
            if globals()["is_orchestrator"]:
                dmatrix_handle = self._synchronize(remote_api.XGDMatrixCreateFromEncryptedFile, request)
            else:
                dmatrix_handle = remote_api.XGDMatrixCreateFromEncryptedFile(request)

            return remote_pb2.Name(name=dmatrix_handle)
        except:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Name(name=None)

    def rpc_XGBoosterSetParam(self, request, context):
        """
        Set booster parameter
        """
        try:
            if globals()["is_orchestrator"]:
                self._synchronize(remote_api.XGBoosterSetParam, request)
            else:
                remote_api.XGBoosterSetParam(request)
            return remote_pb2.Status(status=0)
        except:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Status(status=-1)

    def rpc_XGBoosterCreate(self, request, context):
        """
        Create a booster
        """
        try:
            if globals()["is_orchestrator"]:
                booster_handle = self._synchronize(remote_api.XGBoosterCreate, request)
            else:
                booster_handle = remote_api.XGBoosterCreate(request)
            return remote_pb2.Name(name=booster_handle)
        except:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])
    
            return remote_pb2.Name(name=None)

    def rpc_XGBoosterUpdateOneIter(self, request, context):
        """
        Update model for one iteration
        """
        try:
            if globals()["is_orchestrator"]:
                _ = self._synchronize(remote_api.XGBoosterUpdateOneIter, request)
            else:
                remote_api.XGBoosterUpdateOneIter(request)
            return remote_pb2.Status(status=0)
        except:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Status(status=-1)

    def rpc_XGBoosterPredict(self, request, context):
        """
        Get encrypted predictions
        """
        try:
            enc_preds_list, num_preds_list = [], []
            if globals()["is_orchestrator"]:
                # With a cluster, we'll obtain a set of predictions for each node in the cluster
                enc_preds_list, num_preds_list = self._synchronize(remote_api.XGBoosterPredict, request)

                # If not using a cluster, make the single set of predictions into a list
                if not isinstance(enc_preds_list, list):
                    enc_preds_list = [enc_preds_list]
                if not isinstance(num_preds_list, list):
                    num_preds_list = [num_preds_list]
            else:
                # If we're not the orchestrator, we're just running this on our partition of the data
                enc_preds, num_preds = remote_api.XGBoosterPredict(request)
                enc_preds_list = [enc_preds]
                num_preds_list = [num_preds]

            enc_preds_proto_list = []
            print("We've collected {} predictions".format(len(enc_preds_list)))
            for i in range(len(enc_preds_list)):
                enc_preds = enc_preds_list[i]
                num_preds = num_preds_list[i]

                enc_preds_proto = pointer_to_proto(enc_preds, num_preds * ctypes.sizeof(ctypes.c_float) + CIPHER_IV_SIZE + CIPHER_TAG_SIZE)
                enc_preds_proto_list.append(enc_preds_proto)
            return remote_pb2.Predictions(predictions=enc_preds_proto_list, num_preds=num_preds_list, status=0)

        except Exception as e:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Predictions(predictions=None, num_preds=None, status=-1)

    # FIXME: save model only for rank 0 enclave
    def rpc_XGBoosterSaveModel(self, request, context):
        """
        Save model to encrypted file
        """
        try:
            if globals()["is_orchestrator"]:
                _ = self._synchronize(remote_api.XGBoosterSaveModel, request)
            else:
                remote_api.XGBoosterSaveModel(request)
            return remote_pb2.Status(status=0)

        except Exception as e:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Status(status=-1)

    def rpc_XGBoosterLoadModel(self, request, context):
        """
        Load model from encrypted file
        """
        try:
            if globals()["is_orchestrator"]:
                _ = self._synchronize(remote_api.XGBoosterLoadModel, request)
            else:
                remote_api.XGBoosterLoadModel(request)
            return remote_pb2.Status(status=0)

        except Exception as e:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Status(status=-1)

    def rpc_XGBoosterDumpModelEx(self, request, context):
        """
        Get encrypted model dump
        """
        try:
            if globals()["is_orchestrator"]:
                length, sarr = self._synchronize(remote_api.XGBoosterDumpModelEx, request)
            else:
                length, sarr = remote_api.XGBoosterDumpModelEx(request)
            return remote_pb2.Dump(sarr=sarr, length=length, status=0)

        except Exception as e:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Dump(sarr=None, length=None, status=-1)

    def rpc_XGBoosterDumpModelExWithFeatures(self, request, context):
        """
        Get encrypted model dump with features
        """
        try:
            if globals()["is_orchestrator"]:
                length, sarr = self._synchronize(remote_api.XGBoosterDumpModelExWithFeatures, request)
            else:
                length, sarr = remote_api.XGBoosterDumpModelExWithFeatures(request)
            return remote_pb2.Dump(sarr=sarr, length=length, status=0)

        except Exception as e:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Dump(sarr=None, length=None, status=-1)

    def rpc_XGBoosterGetModelRaw(self, request, context):
        """
        Get encrypted raw model dump
        """
        try:
            if globals()["is_orchestrator"]:
                length, sarr = self._synchronize(remote_api.XGBoosterGetModelRaw, request)
            else:
                length, sarr = remote_api.XGBoosterGetModelRaw(request)
            return remote_pb2.Dump(sarr=sarr, length=length, status=0)

        except Exception as e:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Dump(sarr=None, length=None, status=-1)

    def rpc_XGDMatrixNumCol(self, request, context):
        """
        Get number of columns in DMatrix
        """
        try:
            if globals()["is_orchestrator"]:
                ret = self._synchronize(remote_api.XGDMatrixNumCol, request)
            else:
                ret = remote_api.XGDMatrixNumCol(request)
            return remote_pb2.Integer(value=ret)

        except Exception as e:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Integer(value=None)

    def rpc_XGDMatrixNumRow(self, request, context):
        """
        Get number of rows in DMatrix
        """
        try:
            if globals()["is_orchestrator"]:
                ret = self._synchronize(remote_api.XGDMatrixNumRow, request)
            else:
                ret = remote_api.XGDMatrixNumRow(request)
            return remote_pb2.Integer(value=ret)

        except Exception as e:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Integer(value=None)

    def rpc_RabitInit(self, request, context):
        """
        Initialize rabit
        """
        try:
            if globals()["is_orchestrator"]:
                _ = self._synchronize(rabit_remote_api.RabitInit, request)
            else:
                rabit_remote_api.RabitInit(request)
            return remote_pb2.Status(status=0)
        except:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Status(status=-1)


    def rpc_RabitFinalize(self, request, context):
        """
        Notify rabit tracker that everything is done
        """
        try:
            if globals()["is_orchestrator"]:
                _ = self._synchronize(rabit_remote_api.RabitFinalize, request)
            else:
                rabit_remote_api.RabitFinalize(request)
            return remote_pb2.Status(status=0)
        except:
            e = sys.exc_info()
            print("Error type: " + str(e[0]))
            print("Error value: " + str(e[1]))
            traceback.print_tb(e[2])

            return remote_pb2.Status(status=-1)

def serve(enclave, num_workers=10, all_users=[], nodes=[]):
    condition = threading.Condition()
    command = Command()
    globals()["all_users"] = all_users

    # Sort node IPs to ensure that first element in list is rank 0
    # Above is true because of how tracker assigns ranks
    # Nodes will be passed in if this is the orchestrator
    if nodes == []:
        # This is a node in the cluster, i.e. not an orchestrator
        globals()["is_orchestrator"] = False
    else:
        nodes.sort()
        nodes = [addr + ":50051" for addr in nodes]
        globals()["nodes"] = nodes
        globals()["is_orchestrator"] = True
        print(nodes)

    rpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=num_workers))
    remote_pb2_grpc.add_RemoteServicer_to_server(RemoteServicer(enclave, condition, command), rpc_server)
    rpc_server.add_insecure_port('[::]:50051')
    rpc_server.start()
    rpc_server.wait_for_termination()

