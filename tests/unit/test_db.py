#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlalchemy as db
from mock import patch, call, Mock

from goloka.db import (
    Model,
    Manager,
    InvalidModelDeclaration,
    InvalidColumnName,
    EngineNotSpecified,
    MultipleEnginesSpecified)


metadata = db.MetaData()


class DummyUserModel(Model):
    table = db.Table('dummy_user_model', metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('name', db.String(80)),
        db.Column('age', db.Integer),
    )


class TestManager(Manager):

    def __init__(self):
        pass


class ModelEngineTestManager(Manager):

    def __init__(self):
        self.model = Mock()
        self.engine = Mock()


class ModelInputTestManager(Manager):

    def __init__(self, model):
        self.model = model
        self.engine = Mock()


def test_base_model_insert_in_bulk():
    ("Manager#insert_in_bulk opens and closes the connection and makes an INSERT in bulk")

    class MyTestManager(TestManager):
        get_connection = Mock()
        model = Mock()

    manager = MyTestManager()

    connection_mock = manager.get_connection.return_value
    connection_mock.execute.return_value = 'db-response'

    manager.model.table = Mock()
    manager.model.table.insert.return_value = 'INSERT INTO ... blablabla'
    items = ['i1', 'item2']

    manager.insert_in_bulk(items)

    connection_mock.execute.assert_called_once_with('INSERT INTO ... blablabla', ['i1', 'item2'])
    connection_mock.close.assert_called_once_with()


def test_instantiating_model_with_preprocessed_data():
    ("Instantiating a model with preprocessed data")

    class UserTwiceAsOld(Model):
        table = db.Table('twice_as_old_user', metadata,
            db.Column('id', db.Integer, primary_key=True),
            db.Column('name', db.String(80)),
            db.Column('age', db.Integer),
        )

        def preprocess(self, data):
            data['age'] = int(data.get('age', 0)) * 2
            return data

    old_user = UserTwiceAsOld(name='Chuck Norris', age=33)
    old_user.age.should.equal(66)
    old_user.name.should.equal('Chuck Norris')


def test_preprocess_should_return_dict():
    ("Model.preprocess should always return a dict")

    class AnotherUserModel(Model):
        table = db.Table('another_user_model', metadata,
            db.Column('id', db.Integer, primary_key=True),
            db.Column('name', db.String(80)),
            db.Column('age', db.Integer),
        )

        def preprocess(self, data):
            data['age'] = int(data.get('age', 0)) * 2

    AnotherUserModel.when.called_with(name='Chuck Norris', age=33).should.throw(
        InvalidModelDeclaration, 'The model `AnotherUserModel` declares a preprocess method but it does not return a dictionary!')


def test_creating_model_with_invalid_keyword_arguments():
    ("Instantiating a model with invalid fields as keyword "
     "arguments should raise an exception")

    DummyUserModel.when.called_with(inexistent_field='foobar').should.throw(
        InvalidColumnName, "inexistent_field is not a valid column name for the model "
        "tests.unit.test_db.DummyUserModel (['age', 'id', 'name'])")


def test_model_represented_as_string():
    ("A Model should have a string representation")

    u = DummyUserModel(id=1, name='Gabriel', age=25)
    repr(u).should.equal(b'<DummyUserModel id=1>')


def test_model_to_dict():
    "Model.to_dict should return prepare the model data to be serialized"

    j = DummyUserModel(name='Jeez', age=33)

    j.to_dict().should.equal({'age': 33, 'name': 'Jeez'})


def test_model_to_json():
    "Model.to_json should return serialized model data"

    j = DummyUserModel(name='Jeez', age=33)

    j.to_json().should.equal('{"age": 33, "name": "Jeez"}')


def test_model_getattr():
    "Model data should be possible to be retrieved through __getattr__"

    j = DummyUserModel(name='Jeez', age=33)

    j.should.have.property('name').being.equal('Jeez')
    j.should.have.property('__data__').being.equal({'age': 33, 'name': 'Jeez'})


def test_model_get():
    "Model data can be accessed by get"

    instance = DummyUserModel(name='Jeez')

    instance.get('name').should.equal('Jeez')
    instance.get('age').should.be.none
    instance.get('age', 123).should.equal(123)


def test_model_equality():
    "Model equality is based off ID if each has an ID."

    instance = DummyUserModel(id=1, name='Jeez')
    other_instance = DummyUserModel(id=1, name='NotJeez')

    third_instance = DummyUserModel(id=2, name='Jeez')

    instance.should.equal(other_instance)
    instance.should_not.equal(third_instance)


def test_model_equality_no_id():
    "Model equality is based off data if either does not have an ID."

    instance = DummyUserModel(name='Jeez')
    other_instance = DummyUserModel(name='NotJeez')

    third_instance = DummyUserModel(name='Jeez')

    instance.should_not.equal(other_instance)
    instance.should.equal(third_instance)


def test_model_get_engine_inputted_engine():
    ("Getting the engine for a Model should return the `engine` attribute if "
        "it is not None and the inputted engine IS None. Also, it should "
        "return the inputted engine if it is not None and the `engine` attribute "
        "IS None. Otherwise, throw errors.")

    # Given a model instance with no engine specified
    instance = DummyUserModel()

    # When calling get_engine on it with a non-None engine as input
    engine = instance.get_engine("an engine inputted")

    # Then the result is the inputted engine
    engine.should.equal("an engine inputted")


def test_model_get_engine_multiple_engines():
    ("Getting the engine for a Model should return the `engine` attribute if "
        "it is not None and the inputted engine IS None. Also, it should "
        "return the inputted engine if it is not None and the `engine` attribute "
        "IS None. Otherwise, throw errors.")

    # Given a model instance with an engine specified
    instance = DummyUserModel(engine="init engine")

    # When calling get_engine on it with a non-None engine as input
    # Then it should throw a MultipleEnginesSpecified Exception
    instance.get_engine.when.called_with("an engine inputted").should.throw(
        MultipleEnginesSpecified)


def test_model_get_engine_initialized_engine():
    ("Getting the engine for a Model should return the `engine` attribute if "
        "it is not None and the inputted engine IS None. Also, it should "
        "return the inputted engine if it is not None and the `engine` attribute "
        "IS None. Otherwise, throw errors.")

    # Given a model instance with an engine specified
    instance = DummyUserModel(engine="init engine")

    # When calling get_engine with no input
    engine = instance.get_engine()

    # Then the result is the initial engine
    engine.should.equal("init engine")


def test_model_get_engine_no_engines():
    ("Getting the engine for a Model should return the `engine` attribute if "
        "it is not None and the inputted engine IS None. Also, it should "
        "return the inputted engine if it is not None and the `engine` attribute "
        "IS None. Otherwise, throw errors.")

    # Given a model instance with no engine specified
    instance = DummyUserModel()

    # When calling get_engine with no input
    # Then it should throw a EngineNotSpecified Exception
    instance.get_engine.when.called_with().should.throw(
        EngineNotSpecified)


def test_model_using():

    class MyDummyUserModel(DummyUserModel):

        manager = Mock()

    MyDummyUserModel.using("an engine")

    MyDummyUserModel.manager.assert_called_once_with(
        MyDummyUserModel, "an engine")


def test_model_is_persisted_true():
    ("Model#is_persisted evaluates to True if the Model instance "
        "has an id field.")

    instance = DummyUserModel(id=123)
    instance.is_persisted.should.be.true


def test_model_is_persisted_false():
    ("Model#is_persisted evaluates to False if the Model instance "
        "does NOT have an id field.")

    instance = DummyUserModel()
    instance.is_persisted.should.be.false


class MySaveableModel(Model):
    table = db.Table('my_saveable_model', metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('name', db.String(80)),
    )

    get_engine = Mock()


def test_model_save_new():
    "Saving a new model from the database uses its id"

    d = MySaveableModel(name='foobar')

    engine_mock = d.get_engine.return_value

    db_mock = engine_mock.connect.return_value

    result = db_mock.execute.return_value

    # And that the result id is 333
    result.lastrowid = 333

    # And the last inserted params of the result is an empty dict
    # TODO: better explanation?
    result.last_inserted_params.return_value = {}


    d.save().should.equal(d)

    db_mock.execute.call_args.should.have.length_of(2)
    query = db_mock.execute.call_args[0][0]
    str(query).should.equal(
        'INSERT INTO my_saveable_model (name) VALUES (:name)')


def test_model_save_existing():
    "Saving an existing model from the database uses its id"

    d = MySaveableModel(id=1, name='foobar')

    engine_mock = d.get_engine.return_value

    db_mock = engine_mock.connect.return_value

    result = db_mock.execute.return_value

    # And that the result id is 333
    result.lastrowid = 333

    # And the last inserted params of the result is an empty dict
    # TODO: better explanation?
    result.last_updated_params.return_value = {}

    d.save().should.equal(d)

    db_mock.execute.call_args.should.have.length_of(2)
    query = db_mock.execute.call_args[0][0]
    str(query).should.equal(
        'UPDATE my_saveable_model SET id=:id, name=:name WHERE my_saveable_model.id = :id_1')


class MyDeletableModel(Model):
    table = db.Table('my_deletable_model', metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('name', db.String(80)),
    )

    get_engine = Mock()


def test_model_delete():
    "Deleting a model from the database uses its id"

    d = MyDeletableModel(id=1, name='foobar')

    db_mock = d.get_engine.return_value.connect.return_value
    d.delete().should.equal(db_mock.execute.return_value)

    db_mock.execute.call_args.should.have.length_of(2)
    query = db_mock.execute.call_args[0][0]
    str(query).should.equal(
        'DELETE FROM my_deletable_model WHERE my_deletable_model.id = :id_1')

def test_manager_find_one_by():

    ("Manager#find_one_by finds one record based on the keyword-arguments.")

    class MyTestManager(TestManager):
        query_by = Mock()
        from_result_proxy = Mock(return_value="the results")

    manager = MyTestManager()

    proxy_mock = manager.query_by.return_value
    proxy_mock.fetchone.return_value = "one record"

    # When Manager#find_one_by is called
    result = manager.find_one_by(keyword_one="first", keyword_two="second")

    # Then Manager#query_by is called with the same keyword arguments
    manager.query_by.assert_called_once_with(
        keyword_one="first", keyword_two="second")

    # And Manager#from_result_proxy is called
    manager.from_result_proxy.assert_called_once_with(proxy_mock, "one record")

    # And the `fetchone` method of the proxy is called
    proxy_mock.fetchone.assert_called_once_with()

    # And the result is equal to the result of `from_result_proxy`
    result.should.equal("the results")


@patch('goloka.db.partial')
def test_manager_find_by(partial):
    ("Manager#find_one_by finds all records matching the keyword arguments.")

    class MyTestManager(TestManager):
        query_by = Mock()
        from_result_proxy = Mock(return_value="the results")

    manager = MyTestManager()

    proxy_mock = manager.query_by.return_value
    proxy_mock.fetchall.return_value = ["one record", "two record", "three record"]

    Models_mock = partial.return_value
    Models_mock.side_effect = lambda x: x

    # When Manager#find_by is called
    result = manager.find_by(keyword_one="first", keyword_two="second")

    # Then Manager#query_by is called with the same keyword arguments
    manager.query_by.assert_called_once_with(
        keyword_one="first", keyword_two="second")

    # And a partial function is formed from the `from_result_proxy` method
    # of Manager and the proxy
    partial.assert_called_once_with(manager.from_result_proxy, proxy_mock)

    # And the `fetchall` method of the proxy is called
    proxy_mock.fetchall.assert_called_once_with()

    # And the result of the partial function is called on the rest of the results
    Models_mock.assert_has_calls([
        call("one record"),
        call("two record"),
        call("three record")
    ])

    # And the result is equal to the result of `from_result_proxy`
    result.should.equal(["one record", "two record", "three record"])


def test_manager_all():

    class MyTestManager(TestManager):
        find_by = Mock(return_value="the result")

    manager = MyTestManager()

    manager.all().should.equal("the result")
    manager.find_by.assert_called_once_with()


def test_manager_get_connection():
    ("Manager#get_connection should call the connect method of the instance's "
        "engine attribute")

    class MyTestManager(TestManager):

        engine = Mock(connect=Mock(return_value="fake connect"))

    # Given a Manager instance whose engine.connect returns a connection
    manager = MyTestManager()

    # When `get_connection` is called
    connection = manager.get_connection()

    # Then `engine.connect` is called
    manager.engine.connect.assert_called_once_with()

    # And the result should equal the result of `engine.connect`
    connection.should.equal("fake connect")


def test_manager_from_result_proxy_without_result():
    "Manager#from_result_proxy without result returns None"

    proxy = Mock()
    proxy.keys.return_value = ['name', 'id', 'age']
    manager = TestManager()
    manager.from_result_proxy(proxy, {}).should.be.none


def test_from_result_proxy_with_result():
    "Manager#from_result_proxy with result"

    proxy = Mock()
    proxy.keys.return_value = ['name', 'id', 'age']

    engine_mock = Mock()
    model = DummyUserModel

    manager = Manager(model, engine_mock)
    manager.from_result_proxy(proxy, ('Foobar', 1, 33)).should.be.a(DummyUserModel)


def test_manager_create():
    "Manager#create should create an instance and save it in the database"

    instance_mock = Mock()

    model_mock = Mock(return_value=instance_mock)
    engine_mock = Mock()

    class MyCreatableManager(TestManager):

        model = model_mock
        engine = engine_mock

    manager = MyCreatableManager()

    d = manager.create(id=1, name='foobar')
    model_mock.assert_called_once_with(engine=engine_mock, id=1, name='foobar')

    d.should.equal(instance_mock.save.return_value)
    instance_mock.save.assert_called_once_with()


def test_manager_get_or_create_when_exists():
    ("Manager#get_or_create should return an existing instance if "
     "it was found in the database")

    find_one_by_mock = Mock()

    class MyFindableManager(TestManager):

        find_one_by = find_one_by_mock

    manager = MyFindableManager()

    d = manager.get_or_create(id=1, name='foobar')
    d.should.equal(find_one_by_mock.return_value)


def test_manager_get_or_create_when_does_not_exist():
    ("Manager#get_or_create should create a new instance if "
     "it was not found in the database")

    find_one_by_mock = Mock()
    find_one_by_mock.return_value = None

    create_mock = Mock()
    create_mock.return_value = None

    class MyFCreatableManager(TestManager):

        find_one_by = find_one_by_mock
        create = create_mock

    manager = MyFCreatableManager()

    d = manager.get_or_create(id=1, name='foobar')
    d.should.equal(create_mock.return_value)


@patch("goloka.db.partial")
def test_manager_execute(partial):
    ("Manager#execute should connect to the db, execute a query"
        "and return resolved models")

    ModelsMock = partial.return_value

    class FakeManager(TestManager):
        get_connection = Mock()
        from_result_proxy = Mock()

    manager = FakeManager()

    connection_mock = manager.get_connection.return_value
    result_proxy_mock = connection_mock.execute.return_value
    result_proxy_mock.fetchall.return_value = ['1st', '2nd', '3rd']

    manager.execute("this is a fake query") #.should.equal(['the first', 'the second', 'the third'])

    manager.get_connection.assert_called_once_with()

    connection_mock.execute.assert_called_once_with("this is a fake query")

    ModelsMock.assert_has_calls([
        call('1st'),
        call('2nd'),
        call('3rd'),
    ])


def test_getattribute_from_model():
    ("Managers should allow getting their column values as instance attributes")

    # Given a DB connection
    connection_mock = Mock()

    # And its result proxy
    result = connection_mock.execute.return_value

    class MyDummyUserModel(DummyUserModel):
        pass

    class MyDummyUserManager(TestManager):
        model = MyDummyUserModel
        get_connection = Mock()
        engine = Mock(connect=Mock(return_value=connection_mock))

    manager = MyDummyUserManager()

    # And that the result id is 333
    result.lastrowid = 333

    # And the last inserted params of the result is an empty dict
    # TODO: better explanation?
    result.last_inserted_params.return_value = {}

    data = {
        "name": "Gabriel",
        "age": '25',
    }
    created = manager.create(**data)

    created.should.have.property('id').being.equal(333)
    created.should.have.property('name').being.equal("Gabriel")
    created.should.have.property('age').being.equal(25)


def test_getattribute_from_model_with_falsy_value():
    ("Managers that were given an empty value are left as they are")

    # Given a DB connection
    connection_mock = Mock()

    class MyDummyUserModel(DummyUserModel):
        pass

    class MyDummyUserManager(TestManager):
        model = MyDummyUserModel
        get_connection = Mock()
        engine = Mock(connect=Mock(return_value=connection_mock))

    manager = MyDummyUserManager()

    # And its result proxy
    result = connection_mock.execute.return_value

    # And that the result id is 333
    result.lastrowid = 333

    # And the last inserted params of the result is an empty dict
    # TODO: better explanation?
    result.last_inserted_params.return_value = {}

    data = {
        "name": "Gabriel",
        "age": '',
    }
    created = manager.create(**data)

    created.should.have.property('id').being.equal(333)
    created.should.have.property('name').being.equal("Gabriel")
    created.should.have.property('age').being.equal('')


def test_query_by():
    ("Manager#query_by should take keyword args and "
     "query by them using an AND clause")

    # Given a DB connection
    connection_mock = Mock()

    class MyDummyUserModel(DummyUserModel):
        pass

    class MyDummyUserManager(TestManager):
        model = MyDummyUserModel
        get_connection = Mock(return_value=connection_mock)

    manager = MyDummyUserManager()

    # And its result proxy
    proxy = connection_mock.execute.return_value

    # When I try to query a manager by some field
    result = manager.query_by(name='foo')

    # Then the result should be the result proxy
    result.should.equal(proxy)

    # And the query must be corretly done
    connection_mock.execute.called.should.be.true

    x = connection_mock.execute.call_args[0][0]
    str(x).should.equal(
        'SELECT dummy_user_model.id, dummy_user_model.name, dummy_user_model.age \n'
        'FROM dummy_user_model \n'
        'WHERE dummy_user_model.name = :name_1 '
        'ORDER BY dummy_user_model.id DESC')
