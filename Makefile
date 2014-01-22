
BUILD_INF=METAINFO/build.inf
.PHONY:all
all:${BUILD_INF}
	python setup.py sdist
	[ -d output ] || mkdir output
	cp dist/pydeploy-*.tar.gz output/
.PHONY:install
install:${BUILD_INF}
	python setup.py install
${BUILD_INF}:
	[ -d METAINFO ] || mkdir METAINFO
	if [ ! -f METAINFO/build.inf ]; then echo "SVN:" > METAINFO/build.inf; echo "BUILD:0" >> METAINFO/build.inf; echo "BUILD_TIME:" >> METAINFO/build.inf;fi
.PHONY:clean
clean:
	-rm -rf build dist pydeploy.egg-info
	-rm -rf output
	-find . -name \*.pyc -exec rm '{}' \;
	
