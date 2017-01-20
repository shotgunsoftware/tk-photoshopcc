﻿
// Copyright (c) 2016 Shotgun Software Inc.
// 
// CONFIDENTIAL AND PROPRIETARY
// 
// This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
// Source Code License included in this distribution package. See LICENSE.
// By accessing, using, copying or modifying this work you indicate your 
// agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
// not expressly granted therein are reserved by Shotgun Software Inc.

#include "./JSON-js/json2.js"
#strict on

__OBJECT_REGISTRY = {};
__WRAPPER_REGISTRY = {};
__GLOBAL_SCOPE_WRAPPERS = undefined;

// This adds a "unique_id" method to any object that's defined.
(function() {
    if ( typeof Object.prototype.unique_id == "undefined" ) {
        var id = 0;
        Object.prototype.unique_id = function() {
            if ( typeof this.__uniqueid == "undefined" ) {
                this.__uniqueid = ++id;
            }
            return this.__uniqueid;
        };
    }
})();

function register_object(wrapper, obj) {
    /*
    Registers a wrapper object and records its relationship to a
    concrete object for future lookups.

    :param wrapper: The wrapper object to register.
    :param obj: The concrete object that the wrapper object wraps.
    */
    if ( obj instanceof Array ) {
        for ( i in obj ) {
            register_object(wrapper, obj[i]);
        }
    }
    else if ( typeof obj == 'object' || typeof obj == 'function' ) {
        __OBJECT_REGISTRY[wrapper.unique_id()] = obj;
        __WRAPPER_REGISTRY[wrapper.unique_id()] = wrapper;
    }
}

function is_wrapper(obj) {
    /*
    Tests whether the given object is a wrapper object.

    :param obj: The object to test.

    :rtype: boolean
    */
    if ( obj instanceof ObjectWrapper ) {
        return true;
    }
    else if ( obj instanceof EnumeratorWrapper ) {
        return true;
    }
    else if ( obj instanceof FunctionWrapper ) {
        return true;
    }
    else if ( obj instanceof MethodDescriptor ) {
        return true;
    }
    else if ( obj['__uniqueid'] != undefined ) {
        return true;
    }

    return false;
}

function prepare_arguments(params) {
    /*
    Prepares the contents of a list of arguments for use
    in the native ExtendScript runtime. If wrapper objects
    are found in the params list, they will be replaced with
    their concrete-object equivalent.

    :param params: The list of arguments to prepare.
    */
    prepped = [];
    
    if ( params == undefined ) {
        return prepped;
    }

    for ( i in params ) {
        arg = params[i];

        if ( arg instanceof Array ) {
            prepped.push(prepare_arguments(arg));
        }
        else if ( is_wrapper(arg) == true ) {
            prepped.push(__OBJECT_REGISTRY[arg['__uniqueid']]);
        }
        else {
            prepped.push(arg);
        }
    }

    return prepped;
}

function ArgumentDescriptor(argument) {
    /*
    An argument descriptor that records available argument data
    in such a way that it can be JSON encoded.

    :param argument: The argument description object from ExtendScript's
                     Reflection interface.
    */
    this.name = argument.name;
    this.dataType = argument.dataType;
    this.defaultValue = argument.defaultValue;
    this.description = argument.description;
    this.help = argument.help;
    this.min = argument.min;
    this.max = argument.max;
}

function MethodDescriptor(method) {
    /*
    A method descriptor that records available method data
    in such a way that it can be JSON encoded.

    :param method: The method description object from ExtendScript's
                   Reflection interface.
    */
    this.name = method.name;
    this.dataType = method.dataType;
    this.defaultValue = method.defaultValue;
    this.description = method.description;
    this.help = method.help;
    this.arguments = [];

    if ( method.arguments != undefined ) {
        for ( i in method.arguments ) {
            argument = method.arguments[i];
            this.arguments.push(new ArgumentDescriptor(argument));
        }
    }

    register_object(this, method);
}

function ObjectWrapper(obj) {
    /*
    A javascript object wrapper. Using ExtendScript's Reflection
    interface, the object will be introspected and all relevant
    data recorded in the ObjectWrapper in such a way that it can
    be JSON encoded.

    :param obj: The concrete object to wrap.
    */
    this.name = obj.reflect.name;
    this.description = obj.reflect.description;
    this.help = obj.reflect.help;
    this.instanceof = obj.constructor.name;
    this.properties = [];
    this.methods = {};

    for ( i in obj.reflect.properties ) {
        prop = obj.reflect.properties[i];
        this.properties.push(prop.name);
    }

    for ( i in obj.reflect.methods ) {
        method_info = obj.reflect.methods[i];
        this.methods[method_info.name] = new MethodDescriptor(method_info);
    }

    register_object(this, obj);
}

function FunctionWrapper(func, name) {
    /*
    A javascript function wrapper. Using ExtendScript's Reflection
    interface, the function will be introspected and all relevant
    data recorded in the FunctionWrapper in such a way that it can
    be JSON encoded.

    :param func: The function to wrap.
    :param name: The name of the function as defined in the global
                 scope.
    */
    this.name = name;
    this.description = "";
    this.help = "";
    this.instanceof = "Function";
    this.properties = [];
    this.methods = {};
    this.arguments = [];

    if ( func.arguments != undefined ) {
        for ( i in func.arguments ) {
            argument = func.arguments[i];
            this.arguments.push(new ArgumentDescriptor(argument));
        }
    }

    register_object(this, func);
}

function EnumeratorWrapper(enumerator, name) {
    /*
    An enumerator object wrapper. Enumerators in ExtendScript
    are special and cannot be introspected in the way that other
    objects can be via ExtendScript's Reflection interface. As a
    result, the enumerator is wrapped minimally in such a way that
    it can be JSON encoded.

    :param enumerator: The enumerator object to wrap.
    :param name: The name of the enumerator as defined in the global
                 scope.
    */
    this.name = name;
    this.description = "";
    this.help = "";
    this.instanceof = "Enumerator";
    this.properties = [];
    this.methods = {};

    register_object(this, enumerator);
}

function rpc_new(class_name) {
    /*
    Creates an instance of the class of the given name.

    :param class_name: The name of the class as defined in the global
                       scope.
    */
    // TODO: Need to figure out how to expand arguments for object
    // construction in ECMA3. Sadly, tricks from more modern JS do
    // not work here. Right now we only support no-argument
    // construction.
    var obj = new this[class_name];
    return JSON.stringify(wrap_item(obj, obj.reflect.name));
}

function rpc_get(uid, name) {
    /*
    Gets the value of the property of the given name as defined on the
    concrete object identified by the given unique id.

    :param uid: The unique id of the concrete object.
    :param name: The name of the property to get the value of.
    */
    var obj = __OBJECT_REGISTRY[uid];
    var value = obj[name];

    return JSON.stringify(wrap_item(value, name));
}

function rpc_get_index(uid, index) {
    /*
    Gets the value at the given index of the concrete object identified
    by the given unique id.

    :param uid: The unique id of the concrete object.
    :param index: The index number to get the value of.
    */
    var obj = __OBJECT_REGISTRY[uid];
    var value = obj[index];

    return JSON.stringify(wrap_item(value, index));
}

function rpc_set(uid, name, value) {
    /*
    Sets the property of the given name on the concrete object,
    identified by the given unique id, to the given value.

    :param uid: The unique id of the concrete object.
    :param name: The name of the property to set.
    :param value: The value to set the property to.
    */
    var obj = __OBJECT_REGISTRY[uid];
    var value = value;

    if ( is_wrapper(value) ) {
        value = __OBJECT_REGISTRY[value['__uniqueid']];
    }

    obj[name] = value;
}

function rpc_call(uid, params, bound_parent_uid) {
    /*
    Calls the given callable as identified by the given unique
    id. Parameters given will be prepared for use in the local
    runtime using prepare_arguments() and then passed on to the
    callable at call time. If a bound_parent_uid is given, the
    callable will be call as a method of the concrete object that
    it identifies. If the bound_parent_id is undefined, the
    callable will be called as if it were defined as a function
    in the global scope.

    :param uid: The unique id of the concrete callable object.
    :param params: The list of arguments to provide the callable
                   when it is called.
    :param bound_parent_uid: The parent concrete object, if any,
                             of the callable.
    */
    var obj = __OBJECT_REGISTRY[uid];
    var wrapper = __WRAPPER_REGISTRY[uid];
    var result;
    var args = prepare_arguments(params);

    if ( bound_parent_uid != undefined && bound_parent_uid != -1 ) {
        var parent = __OBJECT_REGISTRY[bound_parent_uid];
        result = parent[wrapper.name].apply(parent, args);
    }
    else {
        result = this[wrapper.name].apply(this, args);
    }

    if ( result != undefined ) {
        return JSON.stringify(wrap_item(result, result.reflect.name));
    }
    else {
        return;
    }
}

function wrap_item(item, name) {
    /*
    Wraps the given concrete object according to its type. If a
    name is given, that name will be passed to the wrapper class
    during instantiation in order to be recorded in the resulting
    wrapper object.

    :param item: The concrete object to wrap.
    :param name: The name of the object, if any.
    */
    if ( item instanceof Array ) {
        var wrappers = [];

        for ( i in item ) {
            wrappers.append(wrap_item(item[i], item[i].reflect.name));
        }

        return wrappers;
    }
    else {
        if ( typeof item == 'function' ) {
            return new FunctionWrapper(item, name);
        }
        else if ( typeof item != 'object' ) {
            return item;
        }
        else {
            try {
                return new ObjectWrapper(item);
            }
            catch(e) {
                if ( e == "Error: Invalid enumeration value" ) {
                    return new EnumeratorWrapper(item, name);
                }
                else {
                    return new EnumeratorWrapper(item, name);
                }
            }
        }
    }
}

function map_global_scope() {
    /*
    Introspects the global scope and wraps all objects, functions,
    variables, enumerators, and classes found. These wrappers are
    registered using register_object(), stored in a container object
    by name, and then JSON encoded before being returned as a string.
    */
    if ( __GLOBAL_SCOPE_WRAPPERS != undefined ) {
        return JSON.stringify(__GLOBAL_SCOPE_WRAPPERS);
    }

    var variables = this.reflect.properties;
    var functions = this.reflect.methods;
    var wrappers = {};

    for ( i in variables ) {
        var var_name = variables[i].name;
        var variable = this[var_name];

        if ( variable != undefined ) {
            wrappers[var_name] = wrap_item(variable, var_name);
        }
    }

    for ( i in functions ) {
        var func_name = functions[i].name;
        var func = this[functions[i].name];

        if ( func != undefined ) {
            wrappers[func_name] = wrap_item(func, func_name);
        }
    }

    // Some things don't end up in the scope's reflection interface
    // for whatever reason. We'll have to force them into the scope
    // wrapper list ourselves.
    var add_items = ["charIDToTypeID", "executeAction"];

    for ( i in add_items ) {
        var item_name = add_items[i];
        var item = this[item_name];

        if ( item != undefined ) {
            wrappers[item_name] = wrap_item(item, item_name);
        }
    }

    // The dollar ($) object also needs to be passed over. We're going
    // to replace the special character with the name "dollar" as that
    // is how the object is referred to in ExtendScript docs from Adobe.
    wrappers["dollar"] = wrap_item($, "dollar");

    __GLOBAL_SCOPE_WRAPPERS = wrappers;
    return JSON.stringify(wrappers);
}


