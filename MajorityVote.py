from sklearn import datasets
from sklearn.model_selection import train_test_split as tts
from sklearn.preprocessing import LabelEncoder, StandardScaler

# load iris to do classification with majorityVoteClassifier
iris = datasets.load_iris()
X, y = iris.data[50:, [1, 2]], iris.target[50:]
le = LabelEncoder()
y = le.fit_transform(y)

X_train, X_test, y_train, y_test = tts(X, y, test_size=0.5, random_state=1, stratify=y)

#3 classifier: logisticregression, DecisionTree, KNN
from sklearn.model_selection import cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
import numpy as np

clf1 = LogisticRegression(penalty='l2', C=0.001, random_state=1)
clf2 = DecisionTreeClassifier(max_depth=1, criterion='entropy', random_state=0)
clf3 = KNeighborsClassifier(n_neighbors=1, p=2, metric='minkowski')
#DecisionTree don't need to do standardization
#use pipeline to do standardization and fit
pipe1 = Pipeline([['sc',StandardScaler()], ['clf', clf1]])
pipe3 = Pipeline([['sc',StandardScaler()], ['clf', clf3]])
clf_labels = ['LogisticRegression', 'DecisionTree', 'KNN']
print('10-fold cross validation:\n')
for clf, label in zip([pipe1, clf2, pipe3], clf_labels):
    scores = cross_val_score(estimator=clf, X=X_train, y=y_train, cv=10, scoring='roc_auc')
    print("ROC AUC: %0.2f (+/- %0.2f) [%s]" % (scores.mean(), scores.std(), label))
#ROC AUC: area under curve: when the AUC>0.7 means great accuracy

#then try to use majorityvoteclassification
#use propability and weights to determine the outcome
#self-define majorotyvoteclassifier
from sklearn.base import BaseEstimator
from sklearn.base import ClassifierMixin
from sklearn.base import clone
from sklearn.pipeline import _name_estimators
import operator
import six

class MajorityVoteClassifier(BaseEstimator, ClassifierMixin):
    def __init__(self, classifiers, vote='classlabel', weights=None):
        self.classifiers = classifiers
        self.named_classifiers = {key: value for key, value in _name_estimators(classifiers)}
        self.vote = vote
        self.weights = weights
    
    def fit(self, X, y):
        self.labelnc_ = LabelEncoder()
        self.labelnc_.fit(y)
        self.classes_ = self.labelnc_.classes_
        self.classifiers_ = []
        for clf in self.classifiers:
            fitted_clf = clone(clf).fit(X, self.labelnc_.transform(y))
            self.classifiers_.append(fitted_clf)
        
        return self
    
    def predict(self, X):
        if self.vote == 'probability':
            maj_vote = np.argmax(self.predict_proba(X), axis=1)
        else:
            predictions = np.asarray([clf.predict(X) for clf in self.classifiers_]).T
            maj_vote = np.apply_along_axis(
                lambda x: np.argmax(np.bincount(x, weights=self.weights)), 
                axis=1, arr=predictions)
        maj_vote = self.labelnc_.inverse_transform(maj_vote)
        return maj_vote
    
    def predict_proba(self, X):
        probas = np.asarray([clf.predict_proba(X) for clf in self.classifiers_])
        avg_proba = np.average(probas, axis=0, weights=self.weights)
        return avg_proba
    
    def get_params(self, deep=True):
        if not deep:
            return super(MajorityVoteClassifier, self).get_params(deep=False)
        else:
            out = self.named_classifiers.copy()
            for name, step in six.iteritems(self.named_classifiers):
                for key, value in six.iteritems(step.get_params(deep=True)):
                    out['%s__%s' % (name, key)] = value
            
            return out

#Use MajorityVoteClassifier to classify
mv_clf = MajorityVoteClassifier(classifiers=[pipe1, clf2, pipe3])
clf_labels += ['Majority Vote']
all_clf = [pipe1, clf2, pipe3, mv_clf]
for clf, label in zip(all_clf, clf_labels):
    scores = cross_val_score(estimator=clf, X=X_train, y=y_train, cv=10, scoring='roc_auc')
    print("ROC AUC: %0.2f (+/- %0.2f) [%s]" % (scores.mean(), scores.std(), label))
    
#adjust the parameters of classifiers
from sklearn.metrics import auc, roc_curve
import matplotlib.pyplot as plt
colors = ['black', 'orange', 'blue', 'green']
linestyles = [':', '--', '-.', '-']
for clf, label, clr, ls in zip(all_clf, clf_labels, colors, linestyles):
    #assume the label of the positive class is 1
    y_pred = clf.fit(X_train, y_train).predict_proba(X_test)[:, 1]
    fpr, tpr, thresholds = roc_curve(y_true=y_test, y_score=y_pred)
    roc_auc = auc(x=fpr, y=tpr)
    plt.plot(fpr, tpr, color=clr, linestyle=ls, 
             label = '%s (auc = %0.2f)' % (label, roc_auc))
plt.legend(loc= 'lower right')
plt.plot([0, 1], [0, 1], linestyle='--', color='gray', linewidth=2)
plt.xlim([-0.1, 1.1])
plt.ylim([-0.1, 1.1])
plt.grid(alpha=0.5)
plt.xlabel('False positive rate')
plt.ylabel('True positive rate')
plt.show()

#find the decision area in different classifier
from itertools import product
sc = StandardScaler()
X_train_std = sc.fit_transform(X_train)
x_min = X_train_std[:, 0].min() -1
x_max = X_train_std[:, 0].max() +1
y_min = X_train_std[:, 1].min() -1
y_max = X_train_std[:, 1].max() +1
xx, yy = np.meshgrid(np.arange(x_min, x_max, 0.1), 
                     np.arange(y_min, y_max, 0.1))
f, ax = plt.subplots(nrows=2, ncols=2, sharex='col', sharey='row', figsize=(7, 5))
for idx, clf, tt in zip(product([0, 1], [0, 1]), all_clf, clf_labels):
    clf.fit(X_train_std, y_train)
    Z = clf.predict(np.c_[xx.ravel(), yy.ravel()])
    Z = Z.reshape(xx.shape)
    ax[idx[0], idx[1]].contourf(xx, yy, Z, alpha=0.3)
    ax[idx[0], idx[1]].scatter(X_train_std[y_train == 0, 0],
                               X_train_std[y_train == 0, 1],
                               c='blue',
                               marker='^',
                               s=50)
    ax[idx[0], idx[1]].scatter(X_train_std[y_train == 1, 0],
                               X_train_std[y_train == 1, 1],
                               c='green',
                               marker='o',
                               s=50)
    ax[idx[0], idx[1]].set_title(tt)
    
plt.text(-3.5, -4.5, s='Septal width [standardized]', ha='center',
         va='center', fontsize=12)
plt.text(-12.5, 4.5, s='Petal length [standardized]', ha='center',
         va='center', fontsize=12, rotation=90)
plt.show()
#TO SEE the parameters in the majorityvoteclassifier
mv_clf.get_params()

from sklearn.model_selection import GridSearchCV
params = {'decisiontreeclassifier__max_depth': [1, 2],
          'pipeline-1__clf__C': [0.001, 0.1, 100]}
grid = GridSearchCV(estimator= mv_clf, param_grid=params, cv=10, scoring='roc_auc')
grid.fit(X_train, y_train)
for params, mean_score, scores in zip(grid.cv_results_["params"], 
                                         grid.cv_results_["mean_test_score"], 
                                         grid.cv_results_["std_test_score"]):
    
    print("%0.3f +/- %0.2f %r" % (mean_score, scores.std()/2, params))
    
print('Best parameter: %s' % grid.best_params_)

print('Accuracy: %.2f' % grid.best_score_)    
    
    
    
    























        
        
        






















