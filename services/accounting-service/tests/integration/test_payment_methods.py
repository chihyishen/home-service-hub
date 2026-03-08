from app import models


def test_payment_method_lifecycle(db_session):
    payment_method = models.PaymentMethod(name="Line Pay", is_active=True)
    db_session.add(payment_method)
    db_session.commit()
    db_session.refresh(payment_method)
    assert payment_method.name == "Line Pay"

    all_methods = db_session.query(models.PaymentMethod).all()
    assert any(pm.id == payment_method.id for pm in all_methods)

    payment_method.name = "LinePay"
    payment_method.is_active = False
    db_session.commit()
    db_session.refresh(payment_method)
    assert payment_method.name == "LinePay"
    assert payment_method.is_active is False

    db_session.delete(payment_method)
    db_session.commit()
